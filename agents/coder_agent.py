import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

# Following the Microsoft Agent Framework Python quickstart (see
# https://github.com/microsoft/agent-framework/tree/main/python) we keep the
# agent pipeline modular and function-based so the next stages can register as
# Microsoft Agent Framework tools without introducing classes.

AGENT_CONFIG: Dict[str, object] = {
    "output_directory": Path("artifacts/swaphub"),
    "framework": "react",
    "styling": "css",
    "typescript": True,
    "template_directory": Path("templates"),
    "max_retries": 3,
    "validation": True,
    "requirements_path": Path("requirements/feature-request.md"),
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

    directories = [
        output_dir,
        output_dir / "components",
        output_dir / "pages",
        output_dir / "styles",
        output_dir / "assets",
        output_dir / "utils",
    ]

    files: List[Dict[str, object]] = []

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


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    requirements_path = Path(AGENT_CONFIG["requirements_path"])
    raw_text = load_requirements_text(requirements_path)
    structured_payload = analyze_requirements(raw_text)
    project_plan = plan_project_structure(structured_payload, AGENT_CONFIG)
    ensure_project_structure(project_plan)
    print(json.dumps({
        "structured_requirements": structured_payload,
        "project_plan": project_plan,
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
