"""Agent that executes generated Playwright tests through the Playwright MCP server."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import subprocess
import time
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

from agent_framework import MCPStdioTool, ai_function
from agent_framework.anthropic import AnthropicClient
from anthropic import AsyncAnthropicFoundry
from dotenv import load_dotenv
from pydantic import Field

# Load environment configuration
load_dotenv()

# Anthropic Foundry configuration (shared with other agents)
ANTHROPIC_FOUNDRY_ENDPOINT = os.getenv("ANTHROPIC_FOUNDRY_ENDPOINT")
ANTHROPIC_FOUNDRY_DEPLOYMENT = os.getenv("ANTHROPIC_FOUNDRY_DEPLOYMENT")
ANTHROPIC_FOUNDRY_API_KEY = os.getenv("ANTHROPIC_FOUNDRY_API_KEY")

# Default location for the generated Playwright test plan
DEFAULT_TEST_PLAN_PATH = Path("artifacts") / "playwright-test-plan.md"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_ROOT = PROJECT_ROOT / "artifacts"
TEST_RESULTS_SUMMARY_FILENAME = "playwright-test-results-summary.txt"

DEFAULT_SERVER_COMMAND = ["python", "-m", "http.server", "8000"]
DEFAULT_SERVER_CWD = Path("artifacts") / "digital-experience-healthcare"
SERVER_READY_TIMEOUT = 15
SERVER_CHECK_INTERVAL = 0.5


def create_playwright_mcp_tool() -> MCPStdioTool:
    """Instantiate the Playwright MCP tool using the same configuration as other agents."""
    return MCPStdioTool(
        name="Playwright MCP",
        description="Runs Playwright MCP Tools.",
        command="npx",
        args=["-y", "@playwright/mcp@latest"],
    )


def read_test_plan(plan_path: Path) -> str:
    """Load the generated Playwright test plan from disk."""
    if not plan_path.exists():
        raise FileNotFoundError(
            f"Test plan not found at {plan_path}. Generate it before running this agent."
        )
    return plan_path.read_text(encoding="utf-8").strip()


def build_execution_prompt(plan_markdown: str) -> str:
    """Create the prompt that instructs the agent how to execute the plan."""
    return (
        "You are a QA automation executor. You receive a Playwright test plan in Markdown. "
        "For each suite and scenario, translate the intent into concrete Playwright test steps. "
        "Use the Playwright MCP tool to run the necessary tests against the target application. "
        "Report consolidated pass/fail results, notable logs, and any follow-up actions.\n\n"
        "Playwright Test Plan:\n\n"
        f"{plan_markdown}"
    )


def start_local_server(
    *,
    command: Optional[list[str]] = None,
    cwd: Optional[Path] = None,
    timeout: int = SERVER_READY_TIMEOUT,
) -> subprocess.Popen[str]:
    """Start the local server hosting the generated app."""
    server_cmd = list(command or DEFAULT_SERVER_COMMAND)
    server_cwd = cwd or DEFAULT_SERVER_CWD
    if not server_cwd.is_absolute():
        server_cwd = (PROJECT_ROOT / server_cwd).resolve()

    if not server_cwd.exists():
        raise FileNotFoundError(
            f"Server directory not found at {server_cwd}. Generate the site before running tests."
        )

    process = subprocess.Popen(
        server_cmd,
        cwd=server_cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    start_time = time.time()
    while True:
        if process.poll() is not None:
            raise RuntimeError(
                "Local server terminated unexpectedly before readiness.\n"
                f"Command: {' '.join(server_cmd)}"
            )
        if time.time() - start_time >= timeout:
            process.terminate()
            raise TimeoutError(
                f"Server did not become ready within {timeout} seconds."
            )
        time.sleep(SERVER_CHECK_INTERVAL)
        break

    return process


def stop_local_server(process: subprocess.Popen[str]) -> None:
    """Stop the previously started local server."""
    if process.poll() is not None:
        return
    with contextlib.suppress(Exception):
        process.terminate()
        process.wait(timeout=5)
    if process.poll() is None:
        with contextlib.suppress(Exception):
            process.kill()


def summarize_execution_output(output: str) -> str:
    """Create a structured summary of the MCP execution output."""
    if not output.strip():
        return "No output was produced by PlaywrightRunnerAgent."

    lines = [line.rstrip() for line in output.splitlines() if line.strip()]

    suites: Dict[str, Dict[str, list[str]]] = {}
    current_suite = "General"
    current_scenario = "Overview"

    suites.setdefault(current_suite, {})
    suites[current_suite].setdefault(current_scenario, [])

    for line in lines:
        cleaned = line.strip()
        upper = cleaned.upper()

        if cleaned.startswith("## "):
            title = cleaned[3:].strip()
            if title and not title.lower().startswith("suite"):
                current_suite = title
            else:
                current_suite = title or current_suite
            suites.setdefault(current_suite, {})
            current_scenario = "Overview"
            suites[current_suite].setdefault(current_scenario, [])
            continue

        if cleaned.startswith("###"):
            title = cleaned.lstrip("#").strip()
            current_scenario = title or current_scenario
            suites.setdefault(current_suite, {})
            suites[current_suite].setdefault(current_scenario, [])
            continue

        status_keywords = ("✅", "❌", "⚠️", "⏭️", "PASS", "FAIL", "ERROR", "WARN")
        if any(keyword in upper for keyword in status_keywords) or cleaned.startswith("-"):
            suites[current_suite].setdefault(current_scenario, []).append(cleaned)

    summary_lines = ["# Playwright MCP Test Summary", ""]

    for suite_name, scenarios in suites.items():
        summary_lines.append(f"## {suite_name}")
        for scenario_name, entries in scenarios.items():
            summary_lines.append(f"### {scenario_name}")
            if not entries:
                summary_lines.append("- (no details captured)")
                continue
            for entry in entries:
                bullet = entry
                if not bullet.startswith("-"):
                    bullet = f"- {bullet}"
                summary_lines.append(bullet)
            summary_lines.append("")
        summary_lines.append("")

    summary = "\n".join(summary_lines).strip()
    return summary + "\n"


def write_summary_file(summary_text: str) -> Path:
    """Persist the summary to the artifacts directory and return the path."""
    ARTIFACTS_ROOT.mkdir(parents=True, exist_ok=True)
    summary_path = ARTIFACTS_ROOT / TEST_RESULTS_SUMMARY_FILENAME
    summary_path.write_text(summary_text, encoding="utf-8")
    return summary_path


async def run_playwright_test_agent(
    plan_path: Path,
    *,
    echo: bool = False,
    start_server: bool = True,
    server_command: Optional[list[str]] = None,
    server_cwd: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute the generated tests via the Playwright MCP server."""
    required_env = {
        "ANTHROPIC_FOUNDRY_ENDPOINT": ANTHROPIC_FOUNDRY_ENDPOINT,
        "ANTHROPIC_FOUNDRY_DEPLOYMENT": ANTHROPIC_FOUNDRY_DEPLOYMENT,
        "ANTHROPIC_FOUNDRY_API_KEY": ANTHROPIC_FOUNDRY_API_KEY,
    }
    missing = [name for name, value in required_env.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing environment variables: " + ", ".join(missing)
        )

    plan_markdown = read_test_plan(plan_path)
    prompt = build_execution_prompt(plan_markdown)

    server_process: Optional[subprocess.Popen[str]] = None
    if start_server:
        server_process = start_local_server(
            command=server_command,
            cwd=server_cwd,
        )

    client = AnthropicClient(
        model_id=ANTHROPIC_FOUNDRY_DEPLOYMENT,
        anthropic_client=AsyncAnthropicFoundry(
            api_key=ANTHROPIC_FOUNDRY_API_KEY,
            base_url=ANTHROPIC_FOUNDRY_ENDPOINT,
        ),
    )

    instructions = (
        "You are PlaywrightRunnerAgent. When the user provides a Playwright test plan, "
        "parse the scenarios, call the Playwright MCP tool to execute the relevant tests, "
        "and provide a detailed but concise report of execution results."
    )

    transcript = []

    agent_kwargs = {
        "name": "PlaywrightRunnerAgent",
        "instructions": instructions,
        "tools": [create_playwright_mcp_tool()],
        "allow_multiple_tool_calls": True,
    }

    try:
        context_manager = client.create_agent(max_output_tokens=8000, **agent_kwargs)
    except TypeError:
        context_manager = client.create_agent(**agent_kwargs)

    try:
        async with context_manager as agent:
            thread = agent.get_new_thread()
            if echo:
                print("Agent: ", end="", flush=True)
            async for chunk in agent.run_stream(prompt, thread=thread):
                if chunk.text:
                    transcript.append(chunk.text)
                    if echo:
                        print(chunk.text, end="", flush=True)
            if echo:
                print()
    finally:
        if start_server and server_process is not None:
            stop_local_server(server_process)

    output_text = "".join(transcript).strip()
    summary_text = summarize_execution_output(output_text)
    summary_path = write_summary_file(summary_text)
    try:
        relative_summary = summary_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        relative_summary = summary_path.as_posix()

    try:
        relative_plan = plan_path.relative_to(PROJECT_ROOT)
        plan_display_path = relative_plan.as_posix()
    except ValueError:
        plan_display_path = plan_path.as_posix()

    return {
        "plan_path": plan_display_path,
        "output": output_text,
        "output_preview": output_text[:1000],
        "summary_text": summary_text,
        "summary_file": relative_summary,
    }


@ai_function(
    name="playwright_test_runner",
    description="Executes the generated Playwright test plan using the Playwright MCP server and reports results.",
)
async def run_playwright_tests_tool(
    plan_path: Annotated[Optional[str], Field(description="Path to the Playwright test plan markdown file.")] = None,
    start_host: Annotated[bool, Field(description="Whether to start the local development server before running tests.")] = True,
) -> Dict[str, Any]:
    resolved_path = Path(plan_path) if plan_path else DEFAULT_TEST_PLAN_PATH
    if not resolved_path.is_absolute():
        resolved_path = (PROJECT_ROOT / resolved_path).resolve()

    result = await run_playwright_test_agent(
        resolved_path,
        echo=False,
        start_server=start_host,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run generated Playwright tests using the Playwright MCP server."
    )
    parser.add_argument(
        "--plan",
        type=Path,
        default=DEFAULT_TEST_PLAN_PATH,
        help="Path to the Playwright test plan markdown file (default: artifacts/playwright-test-plan.md)",
    )
    parser.add_argument(
        "--skip-server",
        action="store_true",
        help="Do not start the local HTTP server before executing tests.",
    )
    args = parser.parse_args()

    result = asyncio.run(
        run_playwright_test_agent(
            args.plan,
            echo=True,
            start_server=not args.skip_server,
        )
    )
    if not result["output"]:
        print("No output captured from PlaywrightRunnerAgent.")
    summary_file = result.get("summary_file")
    if summary_file:
        print(f"Summary saved to {summary_file}")


if __name__ == "__main__":
    main()
