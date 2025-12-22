import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
try:
    from anthropic import AsyncAnthropicFoundry
except ImportError:  # pragma: no cover - optional dependency
    AsyncAnthropicFoundry = None  # type: ignore[assignment]

load_dotenv()

# Following the Microsoft Agent Framework Python quickstart (see
# https://github.com/microsoft/agent-framework/tree/main/python) we keep the
# agent pipeline modular and function-based so the next stages can register as
# Microsoft Agent Framework tools without introducing classes.

AGENT_CONFIG: Dict[str, object] = {
    "output_directory": Path("artifacts/swaphub"),
    "site_mode": "static-site",
    "framework": "react",
    "styling": "css",
    "typescript": True,
    "template_directory": Path("templates"),
    "max_retries": 3,
    "validation": True,
    "requirements_path": Path("requirements/feature-request.md"),
    "use_llm": True,
    "llm": {
        "endpoint": os.getenv("ANTHROPIC_FOUNDRY_ENDPOINT", ""),
        "deployment": os.getenv("ANTHROPIC_FOUNDRY_DEPLOYMENT", ""),
        "api_key": os.getenv("ANTHROPIC_FOUNDRY_API_KEY", ""),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        "temperature": 0.15,
        "max_output_tokens": 1500,
    },
}

LOGGER = logging.getLogger("frontend_coder_agent")


def load_requirements_text(requirements_path: Path) -> str:
    if not requirements_path.exists():
        raise FileNotFoundError(f"Requirement file not found: {requirements_path}")
    text = requirements_path.read_text(encoding="utf-8")
    LOGGER.info("Loaded requirements from %s", requirements_path)
    return text


def split_markdown_sections(markdown_text: str) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    current_header = "overview"
    sections[current_header] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            header = stripped.lstrip("#").strip().lower().replace(" ", "_")
            current_header = header or current_header
            sections.setdefault(current_header, [])
            continue
        if not stripped:
            continue
        sections.setdefault(current_header, []).append(stripped)
    return sections


def is_static_mode(config: Dict[str, object]) -> bool:
    return str(config.get("site_mode", "react")).lower() == "static-site"


def extract_ui_requirements(section_map: Dict[str, List[str]]) -> Dict[str, object]:
    must_haves = section_map.get("must-haves", [])
    constraints = section_map.get("constraints", [])

    components = []
    interactions = []
    styling_notes = []

    for bullet in must_haves:
        normalized = bullet.lstrip("- ").strip()
        if "hero" in normalized.lower():
            components.append({
                "name": "HeroSection",
                "type": "section",
                "description": normalized,
            })
        elif "highlights" in normalized.lower() or "categories" in normalized.lower():
            components.append({
                "name": "Highlights",
                "type": "list",
                "description": normalized,
            })
        elif "footer" in normalized.lower():
            components.append({
                "name": "Footer",
                "type": "footer",
                "description": normalized,
            })
        else:
            interactions.append(normalized)

    for rule in constraints:
        note = rule.lstrip("- ").strip()
        styling_notes.append(note)

    structured = {
        "screens": [
            {
                "name": "MarketplaceLanding",
                "description": "Single responsive marketing screen for SwapHub marketplace.",
                "primary_actions": [bullet.lstrip("- ").strip() for bullet in must_haves if "call-to-action" in bullet.lower()],
            }
        ],
        "components": components,
        "styling": {
            "notes": styling_notes,
            "accessibility": [note for note in styling_notes if "semantic" in note.lower() or "alt" in note.lower()],
        },
        "functionality": interactions,
        "constraints": constraints,
    }

    return structured


def analyze_requirements(markdown_text: str) -> Dict[str, object]:
    sections = split_markdown_sections(markdown_text)
    LOGGER.debug("Parsed sections: %s", list(sections.keys()))
    structured = extract_ui_requirements(sections)
    LOGGER.info("Structured requirement payload prepared.")
    return structured


def plan_project_structure(structured_requirements: Dict[str, object], config: Dict[str, object]) -> Dict[str, object]:
    output_dir = Path(config["output_directory"])
    typescript = bool(config.get("typescript", True))
    extension = "tsx" if typescript else "jsx"

    if is_static_mode(config):
        directories = [
            output_dir,
            output_dir / "assets",
        ]

        files: List[Dict[str, object]] = [
            {
                "path": output_dir / "index.html",
                "type": "html",
                "source": structured_requirements,
            },
            {
                "path": output_dir / "styles.css",
                "type": "css",
                "source": structured_requirements,
            },
            {
                "path": output_dir / "script.js",
                "type": "js",
                "source": structured_requirements,
            },
        ]
    else:
        directories = [
            output_dir,
            output_dir / "components",
            output_dir / "pages",
            output_dir / "styles",
            output_dir / "assets",
            output_dir / "utils",
        ]

        files = []

        for screen in structured_requirements.get("screens", []):
            screen_name = screen.get("name", "Landing")
            files.append(
                {
                    "path": output_dir / "pages" / f"{screen_name}.{extension}",
                    "type": "page",
                    "source": screen,
                }
            )

        for component in structured_requirements.get("components", []):
            comp_name = component.get("name", "Component")
            files.append(
                {
                    "path": output_dir / "components" / f"{comp_name}.{extension}",
                    "type": "component",
                    "source": component,
                }
            )
            files.append(
                {
                    "path": output_dir / "styles" / f"{comp_name}.module.css",
                    "type": "style",
                    "source": {
                        "component": component,
                        "styling": structured_requirements.get("styling", {}),
                    },
                }
            )

        files.append(
            {
                "path": output_dir / "styles" / "global.css",
                "type": "global_style",
                "source": structured_requirements.get("styling", {}),
            }
        )

    plan = {
        "base_path": str(output_dir),
        "directories": [str(directory) for directory in directories],
        "files": [
            {
                "path": str(entry["path"]),
                "type": entry["type"],
                "notes": entry.get("source", {}),
            }
            for entry in files
        ],
        "constraints": structured_requirements.get("constraints", []),
        "test_id_requirement": "Include data-testid on interactive elements",
    }

    LOGGER.info(
        "Generated project plan with %d directories and %d files.",
        len(directories),
        len(files),
    )
    return plan


def ensure_project_structure(plan: Dict[str, object]) -> None:
    for directory in plan.get("directories", []):
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        LOGGER.debug("Ensured directory %s", path)


def slugify(value: str) -> str:
    lower = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return lower.lower() or "component"


def build_llm_client(config: Dict[str, object]) -> Optional[Any]:
    llm_config = config.get("llm", {}) if isinstance(config.get("llm"), dict) else {}
    endpoint = llm_config.get("endpoint", "")
    deployment = llm_config.get("deployment", "")
    api_key = llm_config.get("api_key", "")
    api_version = llm_config.get("api_version", "2024-12-01-preview")

    if not endpoint or not deployment or not api_key:
        LOGGER.warning("Anthropic Foundry configuration incomplete; falling back to deterministic templates.")
        return None

    if AsyncAnthropicFoundry is None:
        LOGGER.error("anthropic package not installed. Install with 'pip install anthropic'.")
        return None

    LOGGER.info("Initializing AsyncAnthropicFoundry client for deployment '%s'.", deployment)
    return AsyncAnthropicFoundry(
        api_key=api_key,
        base_url=endpoint
    )


def extract_text_from_response(response: Any) -> Optional[str]:
    if response is None:
        return None

    content = getattr(response, "content", None)
    if isinstance(content, list):
        fragments: List[str] = []
        for item in content:
            if isinstance(item, dict):
                value = item.get("text") or item.get("value")
                if value:
                    fragments.append(value)
            else:
                text_value = getattr(item, "text", None)
                if text_value:
                    fragments.append(text_value)
        if fragments:
            return "".join(fragments).strip()

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
                # Remove opening fence and optional language annotation
                lines = lines[1:]
                # Drop closing fence if present
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                return "\n".join(lines).strip()
    return stripped


async def invoke_llm_chat(
    client: Optional[Any],
    *,
    system_prompt: str,
    user_prompt: str,
    config: Dict[str, object],
) -> Optional[str]:
    if client is None:
        return None

    llm_config = config.get("llm", {}) if isinstance(config.get("llm"), dict) else {}
    deployment = llm_config.get("deployment", "")
    temperature = float(llm_config.get("temperature", 0.15))
    max_tokens = int(llm_config.get("max_output_tokens", llm_config.get("max_tokens", 1500)))

    try:
        response = await client.messages.create(
            model=deployment,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt,
                        }
                    ],
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # pragma: no cover - network errors
        LOGGER.error("LLM call failed: %s", exc)
        return None

    return extract_text_from_response(response)


def build_component_prompt(
    component_spec: Dict[str, object],
    structured_requirements: Dict[str, object],
    config: Dict[str, object],
) -> Dict[str, str]:
    framework = config.get("framework", "react")
    styling = config.get("styling", "css")
    name = component_spec.get("name", "Component")
    comp_type = component_spec.get("type", "component")
    description = component_spec.get("description", "")
    requirement_summary = json.dumps(structured_requirements, indent=2)

    system_prompt = (
        "You are an expert frontend engineer collaborating via the Microsoft Agent Framework. "
        "Return only TypeScript React component source code, nothing else."
    )
    user_prompt = (
        "Generate a {framework} functional component named {name}.\n"
        "Component type: {comp_type}.\n"
        "Component requirement: {description}.\n"
        "Overall requirements summary: {summary}.\n"
        "Styling approach: {styling}.\n"
        "Constraints: include data-testid attributes for interactive elements and import '../styles/{name}.module.css'."
    ).format(
        framework=framework,
        name=name,
        comp_type=comp_type,
        description=description,
        summary=requirement_summary,
        styling=styling,
    )

    return {"system": system_prompt, "user": user_prompt}


def build_style_prompt(component_spec: Dict[str, object], styling_meta: Dict[str, object]) -> Dict[str, str]:
    component_name = component_spec.get("name", "Component")
    accessibility = styling_meta.get("accessibility", [])
    notes = styling_meta.get("notes", [])

    system_prompt = (
        "You are a senior frontend stylist. Return only CSS module content for the associated component."
    )
    user_prompt = (
        "Create a CSS module for component {component}.\n"
        "Accessibility guidance: {accessibility}.\n"
        "General styling notes: {notes}.\n"
        "Ensure the stylesheet defines classes referenced by the component and supports responsive layouts."
    ).format(
        component=component_name,
        accessibility=", ".join(accessibility) if accessibility else "None",
        notes=", ".join(notes) if notes else "None",
    )

    return {"system": system_prompt, "user": user_prompt}


def build_page_prompt(screen_spec: Dict[str, object], structured_requirements: Dict[str, object]) -> Dict[str, str]:
    component_names = [component.get("name", "Component") for component in structured_requirements.get("components", [])]
    system_prompt = (
        "You orchestrate React pages for the Microsoft Agent Framework. Return only valid TSX for the page component."
    )
    user_prompt = (
        "Create a React page named {name}Page.\n"
        "It must import and render the following components in order: {components}.\n"
        "The page should import '../styles/global.css' and wrap content in <main data-testid='marketplace-landing'>."
    ).format(
        name=screen_spec.get("name", "MarketplaceLanding"),
        components=", ".join(component_names) or "HeroSection, Highlights, Footer",
    )

    return {"system": system_prompt, "user": user_prompt}

def _find_component(structured_requirements: Dict[str, object], name: str) -> Optional[Dict[str, object]]:
    for component in structured_requirements.get("components", []):
        if component.get("name", "").lower() == name.lower():
            return component
    return None

async def generate_component_source(
    component_spec: Dict[str, object],
    structured_requirements: Dict[str, object],
    config: Dict[str, object],
    llm_client: Optional[Any],
) -> str:
    if not config.get("use_llm", True):
        return render_tsx_component(component_spec, config)

    prompts = build_component_prompt(component_spec, structured_requirements, config)
    completion = await invoke_llm_chat(
        llm_client,
        system_prompt=prompts["system"],
        user_prompt=prompts["user"],
        config=config,
    )

    if completion:
        return clean_llm_completion(completion)

    return render_tsx_component(component_spec, config)


async def generate_style_source(
    component_spec: Dict[str, object],
    styling_meta: Dict[str, object],
    config: Dict[str, object],
    llm_client: Optional[Any],
) -> str:
    if not config.get("use_llm", True):
        return render_css_module(component_spec, styling_meta)

    prompts = build_style_prompt(component_spec, styling_meta)
    completion = await invoke_llm_chat(
        llm_client,
        system_prompt=prompts["system"],
        user_prompt=prompts["user"],
        config=config,
    )

    if completion:
        return clean_llm_completion(completion)

    return render_css_module(component_spec, styling_meta)


async def generate_page_source(
    screen_spec: Dict[str, object],
    structured_requirements: Dict[str, object],
    config: Dict[str, object],
    llm_client: Optional[Any],
) -> str:
    if not config.get("use_llm", True):
        return render_page_tsx(screen_spec, structured_requirements, config)

    prompts = build_page_prompt(screen_spec, structured_requirements)
    completion = await invoke_llm_chat(
        llm_client,
        system_prompt=prompts["system"],
        user_prompt=prompts["user"],
        config=config,
    )

    if completion:
        return clean_llm_completion(completion)

    return render_page_tsx(screen_spec, structured_requirements, config)


async def generate_static_html_source(
    structured_requirements: Dict[str, object],
    config: Dict[str, object],
    llm_client: Optional[Any],
) -> str:
    if not config.get("use_llm", True):
        return render_static_html(structured_requirements)

    prompts = build_static_html_prompt(structured_requirements)
    completion = await invoke_llm_chat(
        llm_client,
        system_prompt=prompts["system"],
        user_prompt=prompts["user"],
        config=config,
    )

    if completion:
        return clean_llm_completion(completion)

    return render_static_html(structured_requirements)


async def generate_static_css_source(
    structured_requirements: Dict[str, object],
    config: Dict[str, object],
    llm_client: Optional[Any],
) -> str:
    if not config.get("use_llm", True):
        return render_static_css(structured_requirements)

    prompts = build_static_css_prompt(structured_requirements)
    completion = await invoke_llm_chat(
        llm_client,
        system_prompt=prompts["system"],
        user_prompt=prompts["user"],
        config=config,
    )

    if completion:
        return clean_llm_completion(completion)

    return render_static_css(structured_requirements)


async def generate_static_js_source(
    structured_requirements: Dict[str, object],
    config: Dict[str, object],
    llm_client: Optional[Any],
) -> str:
    if not config.get("use_llm", True):
        return render_static_js(structured_requirements)

    prompts = build_static_js_prompt(structured_requirements)
    completion = await invoke_llm_chat(
        llm_client,
        system_prompt=prompts["system"],
        user_prompt=prompts["user"],
        config=config,
    )

    if completion:
        return clean_llm_completion(completion)

    return render_static_js(structured_requirements)


def render_tsx_component(component_spec: Dict[str, object], config: Dict[str, object]) -> str:
    name = component_spec.get("name", "Component")
    description = component_spec.get("description", "")
    comp_type = component_spec.get("type", "section")
    import_path = f"../styles/{name}.module.css"
    data_test_id = f"{slugify(name)}-section"

    body_lines: List[str] = []

    if comp_type == "section":
        body_lines.extend(
            [
                "      <header>",
                f"        <h1 className={{styles.title}}>{description.split(':')[-1].strip() if ':' in description else name}</h1>",
                f"        <p className={{styles.subtitle}}>{description}</p>",
                "        <button className={styles.cta} data-testid=\"primary-cta\">Get Started</button>",
                "      </header>",
            ]
        )
    elif comp_type == "list":
        body_lines.extend(
            [
                "      <section>",
                f"        <h2 className={{styles.heading}}>{name}</h2>",
                "        <ul className={styles.list}>",
                "          <li data-testid=\"highlight-card-1\">Marketplace category placeholder</li>",
                "          <li data-testid=\"highlight-card-2\">Marketplace category placeholder</li>",
                "          <li data-testid=\"highlight-card-3\">Marketplace category placeholder</li>",
                "        </ul>",
                "      </section>",
            ]
        )
    elif comp_type == "footer":
        body_lines.extend(
            [
                "      <footer>",
                "        <nav className={styles.links}>",
                "          <a href='#' data-testid=\"footer-contact\">Contact</a>",
                "          <a href='#' data-testid=\"footer-policy\">Policies</a>",
                "        </nav>",
                "        <p className={styles.copy}>&copy; {new Date().getFullYear()} SwapHub. All rights reserved.</p>",
                "      </footer>",
            ]
        )
    else:
        body_lines.append(f"      <div className={{styles.block}}>{description}</div>")

    jsx_body = "\n".join(body_lines)

    return (
        "import React from 'react';\n"
        f"import styles from '{import_path}';\n\n"
        f"export function {name}() {{\n"
        f"  return (\n"
        f"    <section className={{styles.root}} data-testid=\"{data_test_id}\">\n"
        f"{jsx_body}\n"
        "    </section>\n"
        "  );\n"
        "}\n"
    )


def render_css_module(component_spec: Dict[str, object], styling_meta: Dict[str, object]) -> str:
    base_rules = [
        ".root {",
        "  width: 100%;",
        "  margin: 0 auto;",
        "  padding: 2rem 1.5rem;",
        "  display: flex;",
        "  flex-direction: column;",
        "  gap: 1.5rem;",
        "}",
    ]

    if component_spec.get("type") == "section":
        base_rules.extend(
            [
                ".title {",
                "  font-size: clamp(2rem, 5vw, 3rem);",
                "  font-weight: 700;",
                "}",
                ".subtitle {",
                "  max-width: 48ch;",
                "  color: #3c4043;",
                "}",
                ".cta {",
                "  align-self: flex-start;",
                "  background-color: #2563eb;",
                "  color: #ffffff;",
                "  padding: 0.75rem 1.5rem;",
                "  border-radius: 999px;",
                "  border: none;",
                "}",
            ]
        )
    elif component_spec.get("type") == "list":
        base_rules.extend(
            [
                ".heading {",
                "  font-size: 1.75rem;",
                "}",
                ".list {",
                "  display: grid;",
                "  gap: 1rem;",
                "  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));",
                "}",
                ".list li {",
                "  background: #ffffff;",
                "  border: 1px solid rgba(15, 23, 42, 0.1);",
                "  padding: 1.25rem;",
                "  border-radius: 0.75rem;",
                "}",
            ]
        )
    elif component_spec.get("type") == "footer":
        base_rules.extend(
            [
                ".links {",
                "  display: flex;",
                "  gap: 1rem;",
                "}",
                ".copy {",
                "  color: #64748b;",
                "  font-size: 0.875rem;",
                "}",
            ]
        )

    accessibility_notes = styling_meta.get("accessibility", [])
    if accessibility_notes:
        base_rules.extend(
            [
                "a {",
                "  color: inherit;",
                "}",
                "a:focus {",
                "  outline: 2px solid #2563eb;",
                "  outline-offset: 4px;",
                "}",
            ]
        )

    base_rules.extend(
        [
            "@media (max-width: 768px) {",
            "  .root {",
            "    padding: 1.5rem 1rem;",
            "  }",
            "}",
        ]
    )

    return "\n".join(base_rules) + "\n"


def render_page_tsx(screen_spec: Dict[str, object], structured_requirements: Dict[str, object], config: Dict[str, object]) -> str:
    name = screen_spec.get("name", "MarketplaceLanding")
    components = structured_requirements.get("components", [])
    component_names = [component.get("name", "Component") for component in components]

    imports = [f"import {{ {comp} }} from '../components/{comp}';" for comp in component_names]
    imports.append("\nimport '../styles/global.css';")

    body_lines = [
        "  return (",
        "    <main data-testid=\"marketplace-landing\">",
    ]

    for comp in component_names:
        body_lines.append(f"      <{comp} />")

    body_lines.extend(
        [
            "    </main>",
            "  );",
        ]
    )

    return (
        "import React from 'react';\n"
        + "\n".join(imports)
        + "\n\n"
        + f"export default function {name}Page() {{\n"
        + "\n".join(body_lines)
        + "\n}"
    )


async def generate_code_artifacts(
    plan: Dict[str, object],
    structured_requirements: Dict[str, object],
    config: Dict[str, object],
    llm_client: Optional[Any],
) -> Dict[str, str]:
    artifacts: Dict[str, str] = {}

    for entry in plan.get("files", []):
        path = entry.get("path", "")
        file_type = entry.get("type")
        source = entry.get("notes", {})

        if file_type == "component":
            artifacts[path] = await generate_component_source(source, structured_requirements, config, llm_client)
        elif file_type == "style":
            component_spec = source.get("component", {})
            styling_meta = source.get("styling", {})
            artifacts[path] = await generate_style_source(component_spec, styling_meta, config, llm_client)
        elif file_type == "page":
            artifacts[path] = await generate_page_source(source, structured_requirements, config, llm_client)
        elif file_type == "global_style":
            artifacts[path] = "body {\n  margin: 0;\n  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;\n  background-color: #f8fafc;\n  color: #0f172a;\n}\n"
        elif file_type == "html":
            artifacts[path] = await generate_static_html_source(structured_requirements, config, llm_client)
        elif file_type == "css":
            artifacts[path] = await generate_static_css_source(structured_requirements, config, llm_client)
        elif file_type == "js":
            artifacts[path] = await generate_static_js_source(structured_requirements, config, llm_client)

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
    raw_text = load_requirements_text(requirements_path)
    structured_payload = analyze_requirements(raw_text)
    project_plan = plan_project_structure(structured_payload, AGENT_CONFIG)
    ensure_project_structure(project_plan)
    llm_client = build_llm_client(AGENT_CONFIG)
    artifacts = await generate_code_artifacts(project_plan, structured_payload, AGENT_CONFIG, llm_client)
    written_paths = write_generated_files(artifacts)
    print(json.dumps({
        "structured_requirements": structured_payload,
        "project_plan": project_plan,
        "generated_files": written_paths,
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
