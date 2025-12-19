from pathlib import Path
from typing import Dict, List, Optional

from agent_framework import ai_function

def _load_requirements(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Requirements file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def _build_plan(requirements_text: str) -> Dict[str, object]:
    summary = "Plan implementation of the requirements in a 2-3 page web app."
    steps: List[str] = [
        "Identify required pages, shared layout, and navigation.",
        "Outline components/widgets needed for each requirement.",
        "Define styling strategy and testing hooks (data-testid).",
        "List open questions or ambiguities for follow-up.",
    ]
    assumptions: List[str] = [
        "Project code will be generated into the artifacts directory.",
        "No existing implementation is present (greenfield).",
    ]
    return {
        "summary": summary,
        "steps": steps,
        "assumptions": assumptions,
        "requirements_body": requirements_text,
    }


@ai_function(
    name="create_development_plan",
    description=(
        "Read the requirements document and return a concise development plan with implementation steps and outstanding assumptions."
    ),
)
def create_development_plan(requirements_file: Optional[str] = None) -> Dict[str, object]:
    target = Path(requirements_file or "requirements/feature-request.md")
    requirements_text = _load_requirements(target)
    plan = _build_plan(requirements_text)
    return {
        "requirements_path": str(target),
        "plan": plan,
    }
