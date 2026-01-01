'''
This agent goes through the requirements files and the artifacts folder to write natural language playwright test suite.
Tools:
    - requirements parser (Writes a summary of what was required)
    - artifacts folder parser (Writes a summary of what is present in code)
    - tests generator (Writes test cases for the application)
'''

from agent_framework.azure import AzureOpenAIAssistantsClient
from agent_framework import ChatMessage, ai_function

import json
import os
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
requirements_summary_deployment = os.getenv("AZURE_OPENAI_REQUIREMENTS_SUMMARY_DEPLOYMENT")
code_summary_deployment = os.getenv("AZURE_OPENAI_CODE_SUMMARY_DEPLOYMENT")
test_writer_deployment = os.getenv("AZURE_OPENAI_TEST_WRITER_DEPLOYMENT")

_SUMMARY_FILENAME = "requirements-summary.txt"
_DEFAULT_SECTION_NAME = "Key Points"
_MAX_SECTION_ITEMS = 16
_LLM_SUMMARY_SYSTEM_PROMPT = (
    "You are a senior QA strategist. Read the provided feature request markdown and produce "
    "a concise JSON summary optimized for planning Playwright automated tests."
    " Structure the output as: {\"title\": string, \"sections\": ["
    "{\"name\": string, \"bullets\": [string, ...]}, ...]}."
    "Include every significant requirement, constraint, interaction, accessibility or analytics signal," 
    "but keep each bullet short (<= 160 characters). "
    "Only return valid JSON."
)


def _sanitize_ascii(value: str) -> str:
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
    return " ".join(normalized.split())


def _extract_text_from_response(response: Any) -> Optional[str]:
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
        return _extract_text_from_response(raw)

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    return None


def _parse_llm_summary(raw_text: str) -> Tuple[str, Dict[str, List[str]]]:
    sanitized_text = raw_text.strip()
    try:
        payload = json.loads(sanitized_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Summary output is not valid JSON.") from exc

    title = _sanitize_ascii(str(payload.get("title") or "Requirements Summary"))

    sections_payload: Any = payload.get("sections")
    sections: Dict[str, List[str]] = {}

    def _consume_section(name: str, bullets: Any) -> None:
        normalized_name = _sanitize_ascii(name) if name else _DEFAULT_SECTION_NAME
        if not isinstance(bullets, list):
            return
        cleaned: List[str] = []
        seen: set[str] = set()
        for entry in bullets:
            if not isinstance(entry, str):
                continue
            item = _sanitize_ascii(entry)
            if not item:
                continue
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(item)
            if len(cleaned) >= _MAX_SECTION_ITEMS:
                break
        if cleaned:
            sections[normalized_name] = cleaned

    if isinstance(sections_payload, dict):
        for name, bullets in sections_payload.items():
            _consume_section(str(name), bullets)
    elif isinstance(sections_payload, list):
        for entry in sections_payload:
            if isinstance(entry, dict):
                section_name = str(entry.get("name") or entry.get("title") or _DEFAULT_SECTION_NAME)
                bullets = entry.get("bullets") or entry.get("items") or entry.get("points")
                _consume_section(section_name, bullets)
            elif isinstance(entry, list) and entry:
                _consume_section(_DEFAULT_SECTION_NAME, entry)

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


def _format_summary_text(title: str, sections: dict[str, list[str]]) -> str:
    lines: list[str] = []
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


def _build_assistants_client_kwargs(deployment_name: str) -> Dict[str, Any]:
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT is not configured.")
    if not deployment_name:
        raise ValueError("Azure OpenAI deployment name is not configured for requirements summarization.")
    if not api_key:
        raise ValueError("AZURE_OPENAI_KEY must be configured for requirements summarization.")

    kwargs: Dict[str, Any] = {
        "endpoint": endpoint,
        "deployment_name": deployment_name,
        "api_version": api_version,
        "api_key": api_key,
    }

    return kwargs


async def _summarize_requirements_with_llm(markdown_text: str) -> Tuple[str, Dict[str, List[str]]]:
    client_kwargs = _build_assistants_client_kwargs(requirements_summary_deployment)
    async with AzureOpenAIAssistantsClient(**client_kwargs) as client:
        response = await client.get_response(
            [
                ChatMessage(role="system", text=_LLM_SUMMARY_SYSTEM_PROMPT),
                ChatMessage(role="user", text=f"Requirements markdown:\n\n{markdown_text}"),
            ],
            temperature=0.2,
            max_tokens=900,
        )

    raw_text = _extract_text_from_response(response)
    if not raw_text:
        raise ValueError("Summarization model returned an empty response.")

    return _parse_llm_summary(raw_text)


@ai_function(
    name="requiremnts_file_parser",
    description="Gets the contents of the requirements file and writes a summary of it to feed to the test writer."
)
async def requirements_file_parser():
    '''
    Generates a dynamic summary of the feature request markdown using the configured Azure OpenAI deployment.
    Raises an error if the summarization service is unavailable or returns an invalid response.
    '''
    project_root = Path(__file__).resolve().parent.parent
    requirements_path = project_root / "requirements" / "feature-request.md"

    if not requirements_path.exists():
        raise FileNotFoundError(f"Requirements file not found at {requirements_path}")

    markdown_text = requirements_path.read_text(encoding="utf-8")
    title, sections = await _summarize_requirements_with_llm(markdown_text)

    summary_text = _format_summary_text(title, sections)

    output_path = project_root / "artifacts" / _SUMMARY_FILENAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary_text, encoding="utf-8")

    return {
        "title": title,
        "sections": sections,
        "summary_text": summary_text,
        "summary_file": str(output_path.relative_to(project_root)),
        "requirements_file": str(requirements_path.relative_to(project_root)),
    }
    
    
@ai_function(
    name="generated_code_parser",
    description="Gets the contents of the artifacts folder and writes a summary of it to feed to the test writer."
)
def generated_code_parser():
    '''
    parameters: The output from the coder agent.
    Uses an LLM for summary.
    We will use the code summary deployment LLM here.
    This function will access the artifacts folder and all the files in it.
    This function have helper functions as well like:
        CodeParser(file_path, language)
        Returns AST/semantic summary: endpoints, page routes, component names, visible labels, form fields, id/class attributes found.
        (For web frontends, also return static selectors and accessible names.)
    This will create a seperate summary file for each code file.
    '''
    print('')


@ai_function(
    name="test_generator",
    description="Gets the output from requirement parser and the code parser and write test cases based on that."
)
def test_generator():
    '''
    parameters: 
        - Requirements summary
        - code summary
    Uses an LLM to generate test cases based on both summaries.
    We will use the main agent LLM in this that will take both summaries and generate the test cases.
    '''
    print('')
    

async def main() -> None:
    
    async with AzureOpenAIAssistantsClient(
        endpoint=endpoint,
        api_key=api_key,
        deployment_name=test_writer_deployment,
        api_version="2024-12-01-preview"
    ).create_agent(
        name="TestWriterAgent",
        instructions="""
        """,
        tools=[requirements_file_parser, generated_code_parser, test_generator]
    ) as agent:
        print('')