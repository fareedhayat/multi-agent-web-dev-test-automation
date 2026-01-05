"""
This agent goes through the requirements files and the artifacts folder to write a natural-language Playwright
test suite.

Tools:
    - requirements parser (writes a summary of what was required)
    - artifacts folder parser (writes a summary of what is present in code)
    - tests generator (writes test cases for the application)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from agent_framework import ai_function
from dotenv import load_dotenv

from .test_writer_helpers import (
    SUMMARY_FILENAME,
    TEST_PLAN_FILENAME,
    CODE_SUMMARY_DIRNAME,
    CODE_SUMMARY_EXTENSION,
    format_summary_text,
    summarize_requirements_with_llm,
    collect_artifact_files,
    summarize_code_files,
    generate_test_plan_with_anthropic,
)

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("ANTHROPIC_FOUNDRY_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_OPENAI_REQUIREMENTS_SUMMARY_DEPLOYMENT = os.getenv("AZURE_OPENAI_REQUIREMENTS_SUMMARY_DEPLOYMENT")
AZURE_OPENAI_CODE_SUMMARY_DEPLOYMENT = os.getenv("AZURE_OPENAI_CODE_SUMMARY_DEPLOYMENT")
ANTHROPIC_FOUNDRY_ENDPOINT = os.getenv("ANTHROPIC_FOUNDRY_ENDPOINT")
ANTHROPIC_FOUNDRY_DEPLOYMENT = os.getenv("ANTHROPIC_FOUNDRY_DEPLOYMENT")
ANTHROPIC_FOUNDRY_API_KEY = os.getenv("ANTHROPIC_FOUNDRY_API_KEY")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_ROOT = PROJECT_ROOT / "artifacts"
REQUIREMENTS_PATH = PROJECT_ROOT / "requirements" / "feature-request.md"
CODE_MANIFEST_FILENAME = "manifest.json"


@ai_function(
    name="requiremnts_file_parser",
    description="Gets the contents of the requirements file and writes a summary of it to feed to the test writer.",
)
async def requirements_file_parser() -> Dict[str, Any]:
    """Summarize the feature request markdown with Azure OpenAI and store the result in artifacts."""
    if not REQUIREMENTS_PATH.exists():
        raise FileNotFoundError(f"Requirements file not found at {REQUIREMENTS_PATH}")

    markdown_text = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    title, sections = await summarize_requirements_with_llm(
        markdown_text,
        endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        deployment_name=AZURE_OPENAI_REQUIREMENTS_SUMMARY_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
    )

    summary_text = format_summary_text(title, sections)

    summary_path = ARTIFACTS_ROOT / SUMMARY_FILENAME
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary_text, encoding="utf-8")

    return {
        "title": title,
        "sections": sections,
        "summary_text": summary_text,
        "summary_file": summary_path.relative_to(PROJECT_ROOT).as_posix(),
        "requirements_file": REQUIREMENTS_PATH.relative_to(PROJECT_ROOT).as_posix(),
    }


@ai_function(
    name="generated_code_parser",
    description="Gets the contents of the artifacts folder and writes a summary of it to feed to the test writer.",
)
async def generated_code_parser() -> Dict[str, Any]:
    """Summarize generated frontend artifacts and persist per-file JSON summaries plus a manifest."""
    if not ARTIFACTS_ROOT.exists() or not ARTIFACTS_ROOT.is_dir():
        raise FileNotFoundError(f"Artifacts directory not found at {ARTIFACTS_ROOT}")

    code_files = collect_artifact_files(ARTIFACTS_ROOT)
    if not code_files:
        raise ValueError("No code artifacts found to summarize. Populate the artifacts folder first.")

    summaries = await summarize_code_files(
        code_files,
        endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        deployment_name=AZURE_OPENAI_CODE_SUMMARY_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
    )

    summary_root = ARTIFACTS_ROOT / CODE_SUMMARY_DIRNAME
    summary_root.mkdir(parents=True, exist_ok=True)

    meta_by_path = {meta["relative_path"]: meta for meta in code_files}
    manifest: Dict[str, Any] = {}

    for relative_path, summary in summaries.items():
        summary_relative_path = Path(relative_path).with_suffix(
            Path(relative_path).suffix + CODE_SUMMARY_EXTENSION
        )
        summary_path = summary_root / summary_relative_path
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        serialized_summary = {**summary, "file_path": relative_path}
        summary_path.write_text(json.dumps(serialized_summary, indent=2), encoding="utf-8")

        file_meta = meta_by_path.get(relative_path, {})
        manifest[relative_path] = {
            "summary_file": summary_path.relative_to(PROJECT_ROOT).as_posix(),
            "language": summary.get("language", ""),
            "truncated": bool(file_meta.get("truncated", False)),
            "overview": summary.get("overview", ""),
            "key_components": summary.get("key_components", []),
            "interactions": summary.get("interactions", []),
            "routes": summary.get("routes", []),
            "selectors": summary.get("selectors", []),
            "data_flow": summary.get("data_flow", []),
            "accessibility": summary.get("accessibility", []),
            "analytics": summary.get("analytics", []),
            "test_ideas": summary.get("test_ideas", []),
        }

    manifest_path = summary_root / CODE_MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {
        "summary_directory": summary_root.relative_to(PROJECT_ROOT).as_posix(),
        "manifest_file": manifest_path.relative_to(PROJECT_ROOT).as_posix(),
        "files": manifest,
    }


@ai_function(
    name="test_generator",
    description="Gets the output from requirement parser and the code parser and write test cases based on that.",
)
async def test_generator() -> Dict[str, Any]:
    """Generate a Markdown Playwright test plan using the requirements and code summaries."""
    requirements_summary_path = ARTIFACTS_ROOT / SUMMARY_FILENAME
    if not requirements_summary_path.exists():
        raise FileNotFoundError(
            "Requirements summary not found. Run the requirements parser before generating tests."
        )

    manifest_path = ARTIFACTS_ROOT / CODE_SUMMARY_DIRNAME / CODE_MANIFEST_FILENAME
    if not manifest_path.exists():
        raise FileNotFoundError(
            "Code summary manifest not found. Run the generated code parser before generating tests."
        )

    requirements_summary = requirements_summary_path.read_text(encoding="utf-8")
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest_data, dict) or not manifest_data:
        raise ValueError("Code summary manifest is empty or malformed.")

    test_plan_markdown = await generate_test_plan_with_anthropic(
        requirements_summary=requirements_summary,
        code_manifest=manifest_data,
        endpoint=ANTHROPIC_FOUNDRY_ENDPOINT,
        api_key=ANTHROPIC_FOUNDRY_API_KEY,
        deployment_name=ANTHROPIC_FOUNDRY_DEPLOYMENT,
    )

    test_plan_path = ARTIFACTS_ROOT / TEST_PLAN_FILENAME
    test_plan_path.parent.mkdir(parents=True, exist_ok=True)
    test_plan_path.write_text(test_plan_markdown, encoding="utf-8")

    return {
        "test_plan_file": test_plan_path.relative_to(PROJECT_ROOT).as_posix(),
        "requirements_summary_file": requirements_summary_path.relative_to(PROJECT_ROOT).as_posix(),
        "code_manifest_file": manifest_path.relative_to(PROJECT_ROOT).as_posix(),
        "test_plan_preview": test_plan_markdown[:1000],
    }