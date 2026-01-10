from __future__ import annotations

import json
import logging
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agent_framework import ChatMessage
from agent_framework.anthropic import AnthropicClient
from agent_framework.azure import AzureOpenAIAssistantsClient
from anthropic import AsyncAnthropicFoundry

try:
    from .agent_debug import log_agent_response_metadata
except ImportError:  # pragma: no cover - script execution fallback
    from agent_debug import log_agent_response_metadata  # type: ignore

SUMMARY_FILENAME = "requirements-summary.txt"
TEST_PLAN_FILENAME = "playwright-test-plan.md"
DEFAULT_SECTION_NAME = "Key Points"
MAX_SECTION_ITEMS = 16
LLM_SUMMARY_SYSTEM_PROMPT = (
    "You are a senior QA strategist. Read the provided feature request markdown and produce "
    "a concise JSON summary optimized for planning Playwright automated tests. "
    "Structure the output as: {\"title\": string, \"sections\": ["
    "{\"name\": string, \"bullets\": [string, ...]}, ...]}. "
    "Include every significant requirement, constraint, interaction, accessibility, or analytics signal, "
    "but keep each bullet short (<= 160 characters). Only return valid JSON."
)

SUPPORTED_CODE_SUFFIXES = {
    ".html",
    ".css",
    ".scss",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
}
CODE_FENCE_LANGUAGE = {
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
}
CODE_SUMMARY_DIRNAME = "code-summaries"
CODE_SUMMARY_EXTENSION = ".summary.json"
MAX_CODE_SNIPPET_CHARS = 12000
CODE_SUMMARY_SYSTEM_PROMPT = (
    "You are a senior QA automation engineer preparing Playwright test plans. "
    "Given a single frontend artifact, respond with strict JSON summarizing the behaviors, selectors, routes, "
    "data flow, accessibility, analytics hooks, and high-value test ideas. Use this schema: "
    "{\"overview\": string, \"key_components\": [string], \"interactions\": [string], \"routes\": [string], "
    "\"selectors\": [string], \"data_flow\": [string], \"accessibility\": [string], \"analytics\": [string], "
    "\"test_ideas\": [string]}. Keep each list concise and test-focused. Only return JSON."
)
CODE_SUMMARY_KEYS = [
    "overview",
    "key_components",
    "interactions",
    "routes",
    "selectors",
    "data_flow",
    "accessibility",
    "analytics",
    "test_ideas",
]

TEST_GENERATION_SYSTEM_PROMPT = (
    "You are a senior QA automation engineer preparing a natural-language Playwright test plan. "
    "Start with the heading 'Playwright Test Plan'. Organize into suites and numbered scenarios. "
    "Each scenario must include Goal, Preconditions, Steps, and Assertions as short bullet lists. "
    "Hard limits for brevity: max 4 bullets per section; each bullet <= 100 characters. "
    "Prioritize critical paths, selectors, and edge cases; omit repetitive detail and prose. "
    "Do not return executable code; keep the response concise so the full plan fits in one reply."
)

# Prompt compaction limits to reduce token usage
PLAN_MAX_REQUIREMENTS_CHARS = 2000
PLAN_MAX_FILES = 25
PLAN_MAX_ITEMS_PER_SECTION = 6
PLAN_OVERVIEW_MAX_CHARS = 200

LOGGER = logging.getLogger("playwright_test_writer")


def sanitize_ascii(value: str, *, preserve_newlines: bool = False) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    replacements = {
        "–": "-",
        "—": "-",
        "“": '"',
        "”": '"',
        "’": "'",
        "‘": "'",
        "…": "...",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    if preserve_newlines:
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        lines = [" ".join(line.split()) for line in normalized.split("\n")]
        return "\n".join(lines).strip()
    return " ".join(normalized.split())


def extract_text_from_response(response: Any) -> Optional[str]:
    if response is None:
        return None

    value_attr = getattr(response, "value", None)
    if isinstance(value_attr, str) and value_attr.strip():
        return value_attr.strip()

    text_attr = getattr(response, "text", None)
    if isinstance(text_attr, str) and text_attr.strip():
        return text_attr.strip()

    content = getattr(response, "content", None)
    if isinstance(content, list):
        fragments: List[str] = []
        for item in content:
            if isinstance(item, dict):
                value = item.get("text") or item.get("value")
                if value:
                    fragments.append(str(value))
            else:
                text_value = getattr(item, "text", None)
                if text_value:
                    fragments.append(str(text_value))
        if fragments:
            return "".join(fragments).strip()

    messages = getattr(response, "messages", None)
    if isinstance(messages, list):
        fragments = []
        for message in messages:
            message_text = getattr(message, "text", None)
            if isinstance(message_text, str) and message_text.strip():
                fragments.append(message_text.strip())
            message_content = getattr(message, "content", None)
            if isinstance(message_content, list):
                for item in message_content:
                    if isinstance(item, dict):
                        value = item.get("text") or item.get("value")
                        if isinstance(value, str) and value.strip():
                            fragments.append(value.strip())
                    else:
                        item_text = getattr(item, "text", None)
                        if isinstance(item_text, str) and item_text.strip():
                            fragments.append(item_text.strip())
        if fragments:
            return "\n".join(fragments).strip()

    raw = getattr(response, "raw_representation", None)
    if raw is not None and raw is not response:
        return extract_text_from_response(raw)

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    return None


def _extract_json_object(raw_text: str) -> Dict[str, Any]:
    decoder = json.JSONDecoder()
    text = raw_text.strip()
    if not text:
        raise ValueError("Summary output is empty; cannot parse JSON.")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    idx = 0
    length = len(text)
    while idx < length:
        char = text[idx]
        if char == "{":
            try:
                payload, end_index = decoder.raw_decode(text, idx)
            except json.JSONDecodeError:
                idx += 1
                continue
            if isinstance(payload, dict):
                return payload
            idx = end_index
            continue
        idx += 1

    raise ValueError("Summary output is not valid JSON.")


def parse_llm_summary(raw_text: str) -> Tuple[str, Dict[str, List[str]]]:
    payload = _extract_json_object(raw_text)

    title = sanitize_ascii(str(payload.get("title") or "Requirements Summary"))

    sections_payload: Any = payload.get("sections")
    sections: Dict[str, List[str]] = {}

    def _consume_section(name: str, bullets: Any) -> None:
        normalized_name = sanitize_ascii(name) if name else DEFAULT_SECTION_NAME
        if not isinstance(bullets, list):
            return
        cleaned: List[str] = []
        seen: set[str] = set()
        for entry in bullets:
            if not isinstance(entry, str):
                continue
            item = sanitize_ascii(entry)
            if not item:
                continue
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(item)
            if len(cleaned) >= MAX_SECTION_ITEMS:
                break
        if cleaned:
            sections[normalized_name] = cleaned

    if isinstance(sections_payload, dict):
        for name, bullets in sections_payload.items():
            _consume_section(str(name), bullets)
    elif isinstance(sections_payload, list):
        for entry in sections_payload:
            if isinstance(entry, dict):
                section_name = str(entry.get("name") or entry.get("title") or DEFAULT_SECTION_NAME)
                bullets = entry.get("bullets") or entry.get("items") or entry.get("points")
                _consume_section(section_name, bullets)
            elif isinstance(entry, list) and entry:
                _consume_section(DEFAULT_SECTION_NAME, entry)

    if not sections:
        candidates = {
            key: value
            for key, value in payload.items()
            if key not in {"title", "sections"}
        }
        for name, value in candidates.items():
            _consume_section(str(name), value)

    if not sections:
        raise ValueError("No sections detected in summary output.")

    return title, sections


def format_summary_text(title: str, sections: Dict[str, List[str]]) -> str:
    lines: List[str] = []
    if title:
        lines.append(title)
        lines.append("")

    for section_name, entries in sections.items():
        if not entries:
            continue
        lines.append(f"{section_name}:")
        for entry in entries:
            lines.append(f"- {entry}")
        lines.append("")

    return "\n".join(lines).strip()


def build_assistants_client_kwargs(
    endpoint: Optional[str],
    api_key: Optional[str],
    deployment_name: Optional[str],
    api_version: str,
) -> Dict[str, Any]:
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT is not configured.")
    if not deployment_name:
        raise ValueError("Azure OpenAI deployment name is not configured.")
    if not api_key:
        raise ValueError("AZURE_OPENAI_KEY must be configured.")

    return {
        "endpoint": endpoint,
        "deployment_name": deployment_name,
        "api_version": api_version,
        "api_key": api_key,
    }


def build_anthropic_client(
    endpoint: Optional[str],
    api_key: Optional[str],
    deployment_name: Optional[str],
) -> AnthropicClient:
    if not endpoint:
        raise ValueError("ANTHROPIC_FOUNDRY_ENDPOINT is not configured.")
    if not deployment_name:
        raise ValueError("Anthropic deployment name is not configured.")
    if not api_key:
        raise ValueError("ANTHROPIC_FOUNDRY_API_KEY must be configured.")

    anthropic_client = AsyncAnthropicFoundry(api_key=api_key, base_url=endpoint)
    return AnthropicClient(model_id=deployment_name, anthropic_client=anthropic_client)


async def summarize_requirements_with_llm(
    markdown_text: str,
    *,
    endpoint: Optional[str],
    api_key: Optional[str],
    deployment_name: Optional[str],
    api_version: str,
) -> Tuple[str, Dict[str, List[str]]]:
    client_kwargs = build_assistants_client_kwargs(endpoint, api_key, deployment_name, api_version)
    async with AzureOpenAIAssistantsClient(**client_kwargs) as client:
        response = await client.get_response(
            [
                ChatMessage(role="system", text=LLM_SUMMARY_SYSTEM_PROMPT),
                ChatMessage(role="user", text=f"Requirements markdown:\n\n{markdown_text}"),
            ],
            temperature=0.2,
            max_tokens=900,
        )

    log_agent_response_metadata(
        "RequirementsSummary",
        response,
        logger=LOGGER,
        include_message_count=True,
    )

    raw_text = extract_text_from_response(response)
    if not raw_text:
        raise ValueError("Summarization model returned an empty response.")

    return parse_llm_summary(raw_text)


def language_from_suffix(suffix: str) -> str:
    match suffix.lower():
        case ".html":
            return "HTML"
        case ".css":
            return "CSS"
        case ".scss":
            return "SCSS"
        case ".js":
            return "JavaScript"
        case ".jsx":
            return "JSX"
        case ".ts":
            return "TypeScript"
        case ".tsx":
            return "TSX"
        case _:
            return "PlainText"


def collect_artifact_files(artifacts_root: Path, max_chars: int = MAX_CODE_SNIPPET_CHARS) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    for path in sorted(artifacts_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(artifacts_root)
        if CODE_SUMMARY_DIRNAME in relative.parts:
            continue
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_CODE_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise UnicodeDecodeError(
                exc.encoding,
                exc.object,
                exc.start,
                exc.end,
                f"Unable to decode {path} as UTF-8",
            ) from exc

        truncated = False
        if len(content) > max_chars:
            content = content[:max_chars]
            truncated = True

        files.append({
            "absolute_path": path,
            "relative_path": relative.as_posix(),
            "language": language_from_suffix(suffix),
            "language_hint": CODE_FENCE_LANGUAGE.get(suffix, "plaintext"),
            "content": content,
            "truncated": truncated,
        })

    return files


def normalize_summary_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list):
        candidates = value
    else:
        candidates = []

    normalized: List[str] = []
    seen: set[str] = set()
    for item in candidates:
        if not isinstance(item, str):
            continue
        sanitized = sanitize_ascii(item)
        if not sanitized:
            continue
        lowered = sanitized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(sanitized)
    return normalized


def parse_code_summary_payload(raw_text: str, file_meta: Dict[str, Any]) -> Dict[str, Any]:
    payload = _extract_json_object(raw_text)

    if not isinstance(payload, dict):
        raise ValueError(
            f"Summary output must be a JSON object for {file_meta['relative_path']}"
        )

    summary: Dict[str, Any] = {
        "file_path": file_meta["relative_path"],
        "language": file_meta["language"],
    }

    overview_value = payload.get("overview", "")
    if not isinstance(overview_value, str):
        overview_value = str(overview_value)
    summary["overview"] = sanitize_ascii(overview_value)

    for key in CODE_SUMMARY_KEYS:
        if key == "overview":
            continue
        summary[key] = normalize_summary_list(payload.get(key))

    return summary


async def summarize_code_files(
    code_files: List[Dict[str, Any]],
    *,
    endpoint: Optional[str],
    api_key: Optional[str],
    deployment_name: Optional[str],
    api_version: str,
) -> Dict[str, Dict[str, Any]]:
    if not code_files:
        raise ValueError("No code artifacts found to summarize.")

    client_kwargs = build_assistants_client_kwargs(endpoint, api_key, deployment_name, api_version)
    summaries: Dict[str, Dict[str, Any]] = {}

    async with AzureOpenAIAssistantsClient(**client_kwargs) as client:
        for file_meta in code_files:
            note = "NOTE: Content truncated to first portion for prompt limits.\n" if file_meta["truncated"] else ""
            user_prompt = (
                f"File path: {file_meta['relative_path']}\n"
                f"Language: {file_meta['language']}\n"
                f"{note}"
                "Provide the JSON summary using the specified schema.\n"
                f"```{file_meta['language_hint']}\n{file_meta['content']}\n```"
            )

            response = await client.get_response(
                [
                    ChatMessage(role="system", text=CODE_SUMMARY_SYSTEM_PROMPT),
                    ChatMessage(role="user", text=user_prompt),
                ],
                temperature=0.1,
                max_tokens=1100,
            )

            log_agent_response_metadata(
                f"CodeSummary:{file_meta['relative_path']}",
                response,
                logger=LOGGER,
            )

            raw_text = extract_text_from_response(response)
            if not raw_text:
                raise ValueError(
                    f"Summarization model returned an empty response for {file_meta['relative_path']}"
                )

            summaries[file_meta["relative_path"]] = parse_code_summary_payload(raw_text, file_meta)

    return summaries


def _truncate(text: str, limit: int) -> str:
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def build_test_plan_prompt(
    requirements_summary: str,
    code_manifest: Dict[str, Dict[str, Any]],
) -> str:
    lines: List[str] = []
    # Compact requirements
    lines.append("Requirements Summary\n--------------------")
    lines.append(_truncate(requirements_summary.strip(), PLAN_MAX_REQUIREMENTS_CHARS))
    lines.append("")
    lines.append("Code Artifact Highlights\n-------------------------")

    # Only include up to PLAN_MAX_FILES files to keep prompt small
    for idx, relative_path in enumerate(sorted(code_manifest)):
        if idx >= PLAN_MAX_FILES:
            lines.append("… (additional files omitted) …")
            break
        entry = code_manifest.get(relative_path) or {}
        lines.append(f"File: {relative_path}")
        language = entry.get("language")
        if language:
            lines.append(f"Language: {language}")
        overview = entry.get("overview")
        if overview:
            lines.append(f"Overview: {_truncate(overview, PLAN_OVERVIEW_MAX_CHARS)}")

        # Include only the most actionable sections and cap items
        for key in ("selectors", "interactions", "routes", "test_ideas"):
            values = entry.get(key) or []
            if not values:
                continue
            label = key.replace("_", " ").title()
            lines.append(f"{label}:")
            for item in values[:PLAN_MAX_ITEMS_PER_SECTION]:
                lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines).strip()


async def generate_test_plan_with_anthropic(
    *,
    requirements_summary: str,
    code_manifest: Dict[str, Dict[str, Any]],
    endpoint: Optional[str],
    api_key: Optional[str],
    deployment_name: Optional[str],
) -> str:
    if not code_manifest:
        raise ValueError("Code manifest is empty; cannot generate tests without artifact context.")

    prompt = build_test_plan_prompt(requirements_summary, code_manifest)
    client = build_anthropic_client(endpoint, api_key, deployment_name)

    messages = [
        ChatMessage(role="system", text=TEST_GENERATION_SYSTEM_PROMPT),
        ChatMessage(role="user", text=prompt),
    ]

    response = await client.get_response(messages, temperature=0.2, max_tokens=3200)
    log_agent_response_metadata("TestPlan", response, logger=LOGGER)
    raw_text = extract_text_from_response(response)

    if not raw_text:
        retry_messages = messages + [
            ChatMessage(
                role="user",
                text=(
                    "Your previous reply was empty. Provide the Playwright Test Plan markdown now, "
                    "following the required structure."
                ),
            )
        ]
        response = await client.get_response(retry_messages, temperature=0.2, max_tokens=3200)
        log_agent_response_metadata("TestPlanRetry", response, logger=LOGGER)
        raw_text = extract_text_from_response(response)

    if not raw_text:
        raise ValueError("Test generation model returned an empty response after retry.")

    return sanitize_ascii(raw_text, preserve_newlines=True)
