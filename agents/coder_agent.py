import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from agent_framework import ChatMessage, ai_function
from agent_framework.anthropic import AnthropicClient
from anthropic import AsyncAnthropicFoundry
from dotenv import load_dotenv
from pydantic import Field

try:
    from .agent_debug import log_agent_response_metadata
except ImportError:
    from agent_debug import log_agent_response_metadata

load_dotenv()

AGENT_CONFIG: Dict[str, object] = {
    "output_directory": Path("artifacts"),
    "requirements_path": Path("requirements/feature-request.md"),
    "use_llm": True,
    "llm": {
        "endpoint": os.getenv("ANTHROPIC_FOUNDRY_ENDPOINT", ""),
        "deployment": os.getenv("ANTHROPIC_FOUNDRY_DEPLOYMENT", ""),
        "api_key": os.getenv("ANTHROPIC_FOUNDRY_API_KEY", ""),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        "temperature": 0.15,
        "max_output_tokens": 10000,
    },
}

LOGGER = logging.getLogger("frontend_coder_agent")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
_GLOBAL_CLASS_LIST: List[str] = []


def resolve_workspace_path(relative_path: str) -> Path:
    """Resolve a workspace-relative path and prevent escaping the project root."""
    resolved = (WORKSPACE_ROOT / relative_path).resolve()
    try:
        resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise ValueError(f"Path escapes workspace root: {relative_path}") from exc
    return resolved


@ai_function(
    name="read_text_file",
    description="Read UTF-8 text from a workspace-relative path.",
)
async def tool_read_text_file(
    path: Annotated[str, Field(description="Relative path to the file within the project workspace.")]
) -> str:
    file_path = resolve_workspace_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


@ai_function(
    name="write_text_file",
    description="Write UTF-8 text to a workspace-relative path, creating parent directories as needed.",
)
async def tool_write_text_file(
    path: Annotated[str, Field(description="Destination path for the text file, relative to the workspace.")],
    content: Annotated[str, Field(description="Text content to write to the file.")],
) -> str:
    file_path = resolve_workspace_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)


AGENT_TOOLS: List[Any] = [tool_read_text_file, tool_write_text_file]

AGENT_INSTRUCTIONS_TEMPLATE = (
    "You are CoderAgent, a senior front-end engineer building static deliverables for the brand "
    "'{brand}'.\n"
    "- Follow the latest system prompt for each request without deviating from the scope.\n"
    "- Prioritize semantic HTML, accessible patterns, and production-quality CSS and JavaScript.\n"
    "- Honor project requirements and testing hooks supplied by the orchestrator.\n"
    "- Never invent files beyond the requested plan and always keep outputs deterministic."
)


def build_agent_instructions(metadata: Dict[str, str]) -> str:
    return AGENT_INSTRUCTIONS_TEMPLATE.format(
        brand=metadata.get("brand_name", "the brand")
    )


def load_requirements_text(requirements_path: Path) -> str:
    if not requirements_path.exists():
        raise FileNotFoundError(f"Requirement file not found: {requirements_path}")
    text = requirements_path.read_text(encoding="utf-8")
    LOGGER.info("Loaded requirements from %s", requirements_path)
    return text


def trim_text(value: str, limit: int = 5000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "\n..."  # truncated marker keeps prompt concise


def extract_metadata(markdown_text: str) -> Dict[str, str]:
    brand_match = re.search(r"^#\s*(.+)$", markdown_text, flags=re.MULTILINE)
    brand_name = brand_match.group(1).strip() if brand_match else "Digital Experience"
    body_lines: List[str] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        body_lines.append(stripped)
        if len(body_lines) >= 6:
            break
    overview = " ".join(body_lines) or "Landing page introducing the brand."
    return {
        "brand_name": brand_name,
        "overview": overview,
        "requirements_excerpt": trim_text(markdown_text),
    }


def slugify(value: str) -> str:
    lower = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return lower.lower() or "site"


def build_llm_client(config: Dict[str, object]) -> AnthropicClient:
    llm_config = config.get("llm", {}) if isinstance(config.get("llm"), dict) else {}
    endpoint = llm_config.get("endpoint", "")
    deployment = llm_config.get("deployment", "")
    api_key = llm_config.get("api_key", "")

    if not endpoint or not deployment or not api_key:
        raise RuntimeError("Anthropic Foundry configuration is incomplete. Please set endpoint, deployment, and api key.")

    if AsyncAnthropicFoundry is None:
        raise RuntimeError("anthropic package not installed. Install with 'pip install anthropic'.")

    LOGGER.info("Initializing AsyncAnthropicFoundry client for deployment '%s'.", deployment)
    base_client = AsyncAnthropicFoundry(api_key=api_key, base_url=endpoint)
    return AnthropicClient(model_id=deployment, anthropic_client=base_client)


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
        fragments: List[str] = []
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
    if isinstance(output_text, str):
        return output_text.strip()

    return None


def clean_llm_completion(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2:
            fence = lines[0]
            if fence.startswith("```"):
                lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                return "\n".join(lines).strip()
    return stripped


async def invoke_llm_chat(
    agent: Optional[Any],
    *,
    system_prompt: str,
    user_prompt: str,
    config: Dict[str, object],
) -> Optional[str]:
    if agent is None:
        return None

    llm_config = config.get("llm", {}) if isinstance(config.get("llm"), dict) else {}
    temperature = float(llm_config.get("temperature", 0.15))
    max_tokens = int(llm_config.get("max_output_tokens", llm_config.get("max_tokens", 5000)))

    try:
        response = await agent.run(
            [
                ChatMessage(role="system", text=system_prompt),
                ChatMessage(role="user", text=user_prompt),
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        LOGGER.error("LLM call failed: %s", exc)
        return None

    log_agent_response_metadata(
        "CoderAgent",
        response,
        logger=LOGGER,
        include_message_count=True,
    )

    return extract_text_from_response(response)


def build_site_plan_prompt(requirements_text: str, metadata: Dict[str, str]) -> Dict[str, str]:
    system_prompt = (
        "You are a senior web architect. Respond only with strict JSON."
    )
    schema = {
        "project_name": "Human readable name",
        "project_slug": "kebab-case identifier",
        "pages": [
            {
                "filename": "index.html",
                "display_name": "Home",
                "purpose": "Why this page exists",
                "key_sections": ["Hero", "Highlights"],
                "interactive_targets": ["accordion"]
            }
        ],
        "assets": {
            "css": [
                {
                    "filename": "styles.css",
                    "scope": "global",
                    "notes": "Shared layout, modern styling"
                }
            ],
            "js": [
                {
                    "filename": "script.js",
                    "scope": "global",
                    "notes": "Progressive enhancement behaviors"
                }
            ]
        },
        "testing_focus": ["data-testid hooks that must exist"]
    }
    user_prompt = (
        "Design a static website plan for the brand '{brand}'.\n"
        "Requirements excerpt:\n{requirements}\n\n"
        "Return JSON matching this schema:\n{schema}\n"
        "- Ensure filenames end with '.html', '.css', or '.js'.\n"
        "- Always include an 'index.html' page.\n"
        "- Keep page and asset counts lean but complete.\n"
        "Respond with JSON only."
    ).format(
        brand=metadata.get("brand_name", "the brand"),
        requirements=metadata.get("requirements_excerpt", ""),
        schema=json.dumps(schema, indent=2),
    )
    return {"system": system_prompt, "user": user_prompt}


def normalize_asset_entry(entry: Any, fallback_name: str) -> Dict[str, str]:
    filename = fallback_name
    scope = "global"
    notes = ""
    if isinstance(entry, dict):
        filename = str(entry.get("filename", filename)).strip() or filename
        scope = str(entry.get("scope", scope)).strip() or scope
        notes = str(entry.get("notes", notes)).strip()
    else:
        filename = str(entry).strip() or fallback_name
    if not filename.endswith(('.css', '.js')):
        ext = '.css' if fallback_name.endswith('.css') else '.js'
        filename = f"{slugify(filename)}{ext}"
    return {
        "filename": filename,
        "scope": scope,
        "notes": notes or ("Global styling" if filename.endswith('.css') else "Global interactions"),
    }


def normalize_site_plan(plan: Dict[str, Any], metadata: Dict[str, str], config: Dict[str, object]) -> Dict[str, Any]:
    project_name = plan.get("project_name") or metadata.get("brand_name", "Digital Experience")
    project_slug = slugify(plan.get("project_slug", project_name))
    pages = plan.get("pages") if isinstance(plan.get("pages"), list) else []
    normalized_pages: List[Dict[str, Any]] = []
    used_filenames: set[str] = set()

    if not pages:
        pages = [
            {
                "filename": "index.html",
                "display_name": "Home",
                "purpose": metadata.get("overview", "Primary landing page."),
                "key_sections": ["Hero", "Highlights"],
                "interactive_targets": ["cta"],
            }
        ]

    for index, raw_page in enumerate(pages):
        if not isinstance(raw_page, dict):
            continue
        filename = str(raw_page.get("filename", "")).strip()
        if not filename:
            filename = "index.html" if index == 0 else f"page-{index + 1}.html"
        if not filename.endswith(".html"):
            filename = f"{slugify(filename)}.html"
        base = filename.rsplit(".html", 1)[0]
        counter = 2
        while filename.lower() in used_filenames:
            filename = f"{base}-{counter}.html"
            counter += 1
        used_filenames.add(filename.lower())
        normalized_pages.append(
            {
                "filename": filename,
                "display_name": raw_page.get("display_name") or raw_page.get("title") or raw_page.get("name") or base.replace("-", " ").title(),
                "purpose": raw_page.get("purpose") or raw_page.get("summary") or metadata.get("overview", ""),
                "key_sections": raw_page.get("key_sections") or raw_page.get("sections") or [],
                "interactive_targets": raw_page.get("interactive_targets") or raw_page.get("interactive_elements") or [],
            }
        )

    assets = plan.get("assets") if isinstance(plan.get("assets"), dict) else {}
    css_assets_raw = assets.get("css") if isinstance(assets.get("css"), list) else []
    js_assets_raw = assets.get("js") if isinstance(assets.get("js"), list) else []
    normalized_css = [normalize_asset_entry(entry, "styles.css") for entry in css_assets_raw] or [normalize_asset_entry({}, "styles.css")]
    normalized_js = [normalize_asset_entry(entry, "script.js") for entry in js_assets_raw] or [normalize_asset_entry({}, "script.js")]

    base_path = Path(config["output_directory"]) / project_slug

    plan.update(
        {
            "project_name": project_name,
            "project_slug": project_slug,
            "pages": normalized_pages,
            "assets": {"css": normalized_css, "js": normalized_js},
            "testing_focus": plan.get("testing_focus") or ["data-testid on navigation, CTAs, and interactive widgets"],
            "base_path": str(base_path),
        }
    )
    return plan


def extract_classes_from_html(html: str) -> List[str]:
    classes: set[str] = set()
    for match in re.finditer(r'class\s*=\s*"([^"]+)"', html):
        for cls in match.group(1).split():
            cls = cls.strip()
            if cls:
                classes.add(cls)
    for match in re.finditer(r'data-testid\s*=\s*"([^"]+)"', html):
        classes.add(match.group(1).strip())
    return sorted(classes)


async def generate_site_plan(
    requirements_text: str,
    metadata: Dict[str, str],
    config: Dict[str, object],
    agent: Optional[Any],
) -> Dict[str, Any]:
    if not config.get("use_llm", True):
        raise RuntimeError("LLM usage disabled while generating the site plan.")
    if agent is None:
        raise RuntimeError("LLM client not initialized. Cannot generate the site plan.")

    prompts = build_site_plan_prompt(requirements_text, metadata)
    completion = await invoke_llm_chat(
        agent,
        system_prompt=prompts["system"],
        user_prompt=prompts["user"],
        config=config,
    )
    if not completion:
        raise RuntimeError("LLM returned no planning response.")

    cleaned = clean_llm_completion(completion)
    try:
        plan = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        LOGGER.error("Failed to parse site plan JSON: %s", exc)
        raise RuntimeError("Invalid site plan JSON returned by LLM.") from exc

    return normalize_site_plan(plan, metadata, config)


def ensure_project_structure(plan: Dict[str, Any]) -> None:
    base_path = Path(plan["base_path"])
    base_path.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Ensured project directory %s", base_path)


def build_html_prompt(
    page_spec: Dict[str, Any],
    plan: Dict[str, Any],
    metadata: Dict[str, str],
    requirements_text: str,
) -> Dict[str, str]:
    system_prompt = "You craft semantic, accessible HTML5. Return a complete document."
    plan_snapshot = json.dumps(
        {
            "project_name": plan["project_name"],
            "pages": plan["pages"],
            "assets": plan["assets"],
            "testing_focus": plan.get("testing_focus", []),
        },
        indent=2,
    )
    user_prompt = (
        "Build the '{display}' page for {brand}.\n"
        "Page specification:\n{page_spec}\n\n"
        "Project plan snapshot:\n{plan_snapshot}\n\n"
        "Full requirements excerpt:\n{requirements}\n\n"
        "Constraints:\n"
        "- Link to global './styles.css' and './script.js'.\n"
        "- Include data-testid attributes for navigation, primary CTAs, and interactive elements.\n"
        "- Favor concise, engaging copy and clear section structure.\n"
        "- Ensure the main element uses data-testid='main-content'."
    ).format(
        display=page_spec.get("display_name"),
        brand=metadata.get("brand_name", "the brand"),
        page_spec=json.dumps(page_spec, indent=2),
        plan_snapshot=plan_snapshot,
        requirements=trim_text(requirements_text),
    )
    return {"system": system_prompt, "user": user_prompt}


def build_styles_prompt(plan: Dict[str, Any], metadata: Dict[str, str], requirements_text: str) -> Dict[str, str]:
    system_prompt = "You author modern, responsive CSS. Return only CSS."
    user_prompt = (
        "Create a single stylesheet '{filename}' for {brand}.\n"
        "Project overview:\n{plan_snapshot}\n\n"
        "Requirements excerpt:\n{requirements}\n\n"
        "Style the following classes and patterns comprehensively (include base, components, and responsive rules):\n{class_list}\n\n"
        "Output structure (do not stop until all sections are present):\n"
        "1) CSS Reset + Base Typography\n"
        "2) Layout Utilities (container, grid, spacing)\n"
        "3) Components: navbar, hero, buttons, cards, toast, skip-link, theme-toggle\n"
        "4) Accessibility: focus styles, reduced motion handling hooks\n"
        "5) Dark theme overrides using [data-theme='dark']\n"
        "6) Media queries: 768px and 1200px breakpoints\n"
    ).format(
        filename=plan["assets"]["css"][0]["filename"],
        brand=metadata.get("brand_name", "the brand"),
        plan_snapshot=json.dumps({"pages": plan["pages"], "testing_focus": plan.get("testing_focus", [])}, indent=2),
        requirements=trim_text(requirements_text),
        class_list=json.dumps(sorted(_GLOBAL_CLASS_LIST or []), indent=2),
    )
    return {"system": system_prompt, "user": user_prompt}


def build_script_prompt(plan: Dict[str, Any], metadata: Dict[str, str], requirements_text: str) -> Dict[str, str]:
    system_prompt = "You write defensive, framework-free JavaScript. Return only JS."
    interactive_targets: List[str] = []
    for page in plan["pages"]:
        interactive_targets.extend(page.get("interactive_targets", []))
    if not interactive_targets:
        interactive_targets = ["sticky navigation", "accordion", "form validation"]
    user_prompt = (
        "Create a script '{filename}' for {brand}.\n"
        "Interactive needs: {interactive}.\n"
        "Project testing focus: {testing}.\n"
        "Requirements excerpt:\n{requirements}\n\n"
        "Expectations:\n"
        "- Use data-testid selectors when attaching behavior.\n"
        "- Guard against missing DOM nodes.\n"
        "- Provide keyboard-friendly interactions and focus management.\n"
        "- Avoid external dependencies."
    ).format(
        filename=plan["assets"]["js"][0]["filename"],
        brand=metadata.get("brand_name", "the brand"),
        interactive=", ".join(sorted(set(interactive_targets))),
        testing=", ".join(plan.get("testing_focus", [])),
        requirements=trim_text(requirements_text),
    )
    return {"system": system_prompt, "user": user_prompt}


async def generate_html_page(
    page_spec: Dict[str, Any],
    plan: Dict[str, Any],
    metadata: Dict[str, str],
    requirements_text: str,
    config: Dict[str, object],
    agent: Optional[Any],
) -> str:
    prompts = build_html_prompt(page_spec, plan, metadata, requirements_text)
    completion = await invoke_llm_chat(
        agent,
        system_prompt=prompts["system"],
        user_prompt=prompts["user"],
        config=config,
    )
    if not completion:
        raise RuntimeError(f"LLM returned no HTML for page '{page_spec.get('filename')}'.")
    return clean_llm_completion(completion)


async def generate_stylesheet(
    plan: Dict[str, Any],
    metadata: Dict[str, str],
    requirements_text: str,
    config: Dict[str, object],
    agent: Optional[Any],
) -> str:
    llm_cfg = config.get("llm", {}) if isinstance(config.get("llm"), dict) else {}
    boosted_cfg = {
        **config,
        "llm": {**llm_cfg, "max_output_tokens": max(int(llm_cfg.get("max_output_tokens", 1500)) * 2, 10000)},
    }

    parts: List[str] = []

    p1 = (
        "Write CSS sections: (1) Reset + Base Typography, (2) Layout Utilities (container, grid, spacing). "
        "Use design tokens and class list:\n{classes}"
    ).format(classes=json.dumps(sorted(_GLOBAL_CLASS_LIST or []), indent=2))
    r1 = await invoke_llm_chat(agent, system_prompt="Return only CSS.", user_prompt=p1, config=boosted_cfg)
    if r1:
        parts.append(clean_llm_completion(r1))

    p2 = (
        "Write CSS for components: navbar, hero, buttons (.btn, .btn-primary, .btn-secondary), cards (.intro-card, .service-card), "
        "toast (.toast, .toast-container), skip-link (.skip-link), theme-toggle (.theme-toggle). Include hover/focus/active states. "
        "Class list:\n{classes}"
    ).format(classes=json.dumps(sorted(_GLOBAL_CLASS_LIST or []), indent=2))
    r2 = await invoke_llm_chat(agent, system_prompt="Return only CSS.", user_prompt=p2, config=boosted_cfg)
    if r2:
        parts.append(clean_llm_completion(r2))

    # Pass 3: Accessibility + Dark theme + Media queries
    p3 = (
        "Add accessibility styles (focus-visible outlines, reduced motion hooks), dark theme overrides under [data-theme='dark'], "
        "and responsive media queries for 768px and 1200px breakpoints covering layout and components."
    )
    r3 = await invoke_llm_chat(agent, system_prompt="Return only CSS.", user_prompt=p3, config=boosted_cfg)
    if r3:
        parts.append(clean_llm_completion(r3))

    css_combined = "\n\n".join([p for p in parts if p.strip()])
    if not css_combined.strip():
        raise RuntimeError("LLM returned no CSS output.")
    return css_combined


async def generate_script(
    plan: Dict[str, Any],
    metadata: Dict[str, str],
    requirements_text: str,
    config: Dict[str, object],
    agent: Optional[Any],
) -> str:
    prompts = build_script_prompt(plan, metadata, requirements_text)
    completion = await invoke_llm_chat(
        agent,
        system_prompt=prompts["system"],
        user_prompt=prompts["user"],
        config=config,
    )
    if not completion:
        raise RuntimeError("LLM returned no JavaScript output.")
    return clean_llm_completion(completion)


async def generate_site_artifacts(
    plan: Dict[str, Any],
    metadata: Dict[str, str],
    requirements_text: str,
    config: Dict[str, object],
    agent: Optional[Any],
) -> Dict[str, str]:
    artifacts: Dict[str, str] = {}
    base_path = Path(plan["base_path"])
    css_filename = plan["assets"]["css"][0]["filename"]
    js_filename = plan["assets"]["js"][0]["filename"]
    collected_classes: set[str] = set()

    for page in plan["pages"]:
        html = await generate_html_page(page, plan, metadata, requirements_text, config, agent)
        # Record classes for styling prompt
        for cls in extract_classes_from_html(html):
            collected_classes.add(cls)
        artifacts[str(base_path / page["filename"])] = html

    # Update global class list for styles prompt
    global _GLOBAL_CLASS_LIST
    _GLOBAL_CLASS_LIST = sorted(collected_classes)

    css_content = await generate_stylesheet(plan, metadata, requirements_text, config, agent)
    artifacts[str(base_path / css_filename)] = css_content
    js_content = await generate_script(plan, metadata, requirements_text, config, agent)
    artifacts[str(base_path / js_filename)] = js_content

    return artifacts


def write_generated_files(artifacts: Dict[str, str]) -> List[str]:
    written: List[str] = []
    for raw_path, content in artifacts.items():
        path = Path(raw_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(str(path))
        LOGGER.info("Wrote %s", path)
    return written


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    requirements_path = Path(AGENT_CONFIG["requirements_path"])
    requirements_text = load_requirements_text(requirements_path)
    metadata = extract_metadata(requirements_text)
    llm_client = build_llm_client(AGENT_CONFIG)
    agent_instructions = build_agent_instructions(metadata)
    async with llm_client.create_agent(
        name="CoderAgent",
        instructions=agent_instructions,
        tools=AGENT_TOOLS,
        # Disable tool side effects during content generation to ensure determinism
        allow_multiple_tool_calls=False,
    ) as agent:
        site_plan = await generate_site_plan(requirements_text, metadata, AGENT_CONFIG, agent)
        ensure_project_structure(site_plan)
        artifacts = await generate_site_artifacts(site_plan, metadata, requirements_text, AGENT_CONFIG, agent)
    written_paths = write_generated_files(artifacts)
    print(json.dumps({
        "project_plan": site_plan,
        "generated_files": written_paths,
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
