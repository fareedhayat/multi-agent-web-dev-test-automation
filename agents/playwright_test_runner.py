"""Agent that executes generated Playwright tests through the Playwright MCP server."""

from __future__ import annotations

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

load_dotenv()

ANTHROPIC_FOUNDRY_ENDPOINT = os.getenv("ANTHROPIC_FOUNDRY_ENDPOINT")
ANTHROPIC_FOUNDRY_DEPLOYMENT = os.getenv("ANTHROPIC_FOUNDRY_DEPLOYMENT")
ANTHROPIC_FOUNDRY_API_KEY = os.getenv("ANTHROPIC_FOUNDRY_API_KEY")

DEFAULT_TEST_PLAN_PATH = Path("artifacts") / "playwright-test-plan.md"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_ROOT = PROJECT_ROOT / "artifacts"
TEST_RESULTS_FILENAME = "playwright-test-results.md"

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




async def run_playwright_test_agent(
    plan_path: Path,
    *,
    echo: bool = False,
    start_server: bool = True,
    server_command: Optional[list[str]] = None,
    server_cwd: Optional[Path] = None,
    results_path: Optional[Path] = None,
) -> Dict[str, Any]:
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

    try:
        async with client.create_agent(
            name="PlaywrightRunnerAgent",
            instructions=instructions,
            tools=[create_playwright_mcp_tool()],
            allow_multiple_tool_calls=True,
        ) as agent:
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
    try:
        relative_plan = plan_path.relative_to(PROJECT_ROOT)
        plan_display_path = relative_plan.as_posix()
    except ValueError:
        plan_display_path = plan_path.as_posix()

    resolved_results_path = results_path
    if resolved_results_path is None:
        resolved_results_path = ARTIFACTS_ROOT / TEST_RESULTS_FILENAME
    if not resolved_results_path.is_absolute():
        resolved_results_path = (PROJECT_ROOT / resolved_results_path).resolve()

    resolved_results_path.parent.mkdir(parents=True, exist_ok=True)
    summary_lines = [
        "# Playwright Test Results",
        "",
        f"- Test Plan: {plan_display_path}",
        f"- Generated At: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    ]
    summary_body = output_text or "No output captured from PlaywrightRunnerAgent."
    summary_lines.extend(["", summary_body])
    resolved_results_path.write_text("\n".join(summary_lines), encoding="utf-8")

    try:
        relative_results = resolved_results_path.relative_to(PROJECT_ROOT)
        results_display_path = relative_results.as_posix()
    except ValueError:
        results_display_path = resolved_results_path.as_posix()

    return {
        "plan_path": plan_display_path,
        "output": output_text,
        "output_preview": output_text[:1000],
        "results_file": results_display_path,
    }


@ai_function(
    name="playwright_test_runner",
    description="Executes the generated Playwright test plan using the Playwright MCP server and reports results.",
)
async def run_playwright_tests_tool(
    plan_path: Annotated[Optional[str], Field(description="Path to the Playwright test plan markdown file.")] = None,
    start_host: Annotated[bool, Field(description="Whether to start the local development server before running tests.")] = True,
    results_path: Annotated[Optional[str], Field(description="Optional path for saving the test run summary.")] = None,
) -> Dict[str, Any]:
    resolved_path = Path(plan_path) if plan_path else DEFAULT_TEST_PLAN_PATH
    if not resolved_path.is_absolute():
        resolved_path = (PROJECT_ROOT / resolved_path).resolve()
    resolved_results_path = Path(results_path) if results_path else None
    if resolved_results_path is not None and not resolved_results_path.is_absolute():
        resolved_results_path = (PROJECT_ROOT / resolved_results_path).resolve()

    result = await run_playwright_test_agent(
        resolved_path,
        echo=False,
        start_server=start_host,
        results_path=resolved_results_path,
    )
    return result


def main() -> None:
    plan_path = (PROJECT_ROOT / DEFAULT_TEST_PLAN_PATH).resolve()
    result = asyncio.run(
        run_playwright_test_agent(
            plan_path,
            echo=True,
            start_server=True,
            results_path=None,
        )
    )
    if not result["output"]:
        print("No output captured from PlaywrightRunnerAgent.")
    print(f"Test results saved to: {result['results_file']}")


if __name__ == "__main__":
    main()
