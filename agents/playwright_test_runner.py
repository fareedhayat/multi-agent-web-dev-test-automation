"""Agent that executes generated Playwright tests through the Playwright MCP server."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import socket
import os
import re
import subprocess
import time
import sys
import shutil
from pathlib import Path
from collections import OrderedDict
from typing import Annotated, Any, Dict, Optional

from agent_framework import MCPStdioTool, ai_function
from agent_framework.anthropic import AnthropicClient
from anthropic import AsyncAnthropicFoundry
from dotenv import load_dotenv
from pydantic import Field

try:
    from .agent_debug import log_agent_stream_metadata
except ImportError:
    from agent_debug import log_agent_stream_metadata

try:
    from .agent_metrics import AgentRunMetricsCollector, dump_metrics_to_file
except ImportError:
    from agent_metrics import AgentRunMetricsCollector, dump_metrics_to_file

load_dotenv()

ANTHROPIC_FOUNDRY_ENDPOINT = os.getenv("ANTHROPIC_FOUNDRY_ENDPOINT")
ANTHROPIC_FOUNDRY_DEPLOYMENT = os.getenv("ANTHROPIC_FOUNDRY_DEPLOYMENT")
ANTHROPIC_FOUNDRY_API_KEY = os.getenv("ANTHROPIC_FOUNDRY_API_KEY")

DEFAULT_TEST_PLAN_PATH = Path("artifacts") / "playwright-test-plan.md"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_SERVER_COMMAND = ["python", "-m", "http.server", "8000"]
DEFAULT_SERVER_CWD = Path("artifacts") / "digital-experience-healthcare"
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_LOG_PATH = Path("artifacts") / "playwright-run.log"
SERVER_READY_TIMEOUT = 15
SERVER_CHECK_INTERVAL = 0.5

LOGGER = logging.getLogger("playwright_test_runner")


# def create_playwright_mcp_tool() -> MCPStdioTool:
#     """Instantiate the Playwright MCP tool using the same configuration as other agents."""
#     return MCPStdioTool(
#         name="Playwright MCP",
#         description="Runs Playwright MCP Tools.",
#         command="npx",
#         args=["-y", "@playwright/mcp@latest"],
#     )
# def create_playwright_mcp_tool() -> MCPStdioTool:
#     """Instantiate the Playwright MCP tool using the same configuration as other agents."""
#     return MCPStdioTool(
#         name="selenium",
#         description="Runs Playwright MCP Tools.",
#         command="python",
#         args=["-m", "mcp_server_selenium", "--port", "9222", "--user_data_dir", "artifacts\chrome-debug"],
#     )
def create_playwright_mcp_tool() -> MCPStdioTool:
    """Instantiate the Selenium MCP tool using the packaged executable."""

    mcp_exe = PROJECT_ROOT / ".venv" / "Scripts" / "selenium-mcp-server.exe"
    if not mcp_exe.exists():
        raise FileNotFoundError(
            f"Expected Selenium MCP server at {mcp_exe}. Install selenium-mcp-server in the virtualenv."
        )

    profile_dir = PROJECT_ROOT / "artifacts" / "chrome-debug"
    profile_dir.mkdir(parents=True, exist_ok=True)

    port = int(os.getenv("SELENIUM_MCP_DEBUG_PORT", "9222"))

    _start_chrome_remote_debug(port, profile_dir)

    driver_name = os.getenv("SELENIUM_MCP_DRIVER", "normal_chromedriver")
    driver_path = os.getenv("SELENIUM_MCP_DRIVER_PATH")

    if not driver_path:
        bundled_driver = PROJECT_ROOT / "drivers" / "chromedriver-win64" / "chromedriver.exe"
        if bundled_driver.exists():
            driver_path = str(bundled_driver)

    env_vars = os.environ.copy()

    if driver_path:
        driver_file = Path(driver_path)
        if driver_file.exists():
            driver_file = driver_file.resolve()
            driver_dir = str(driver_file.parent)
            current_path = env_vars.get("PATH", "")
            path_parts = current_path.split(os.pathsep) if current_path else []
            if driver_dir not in path_parts:
                env_vars["PATH"] = (
                    os.pathsep.join([driver_dir, current_path]) if current_path else driver_dir
                )
            env_vars["CHROMEDRIVER"] = str(driver_file)
            env_vars["SELENIUM_MCP_DRIVER_PATH"] = str(driver_file)
        else:
            LOGGER.warning("SELENIUM_MCP_DRIVER_PATH does not exist: %s", driver_path)

    args = [
        "--port",
        str(port),
        "--user_data_dir",
        str(profile_dir),
        "--driver",
        driver_name,
    ]

    return MCPStdioTool(
        name="selenium",
        description="Runs Selenium MCP Tools.",
        command=str(mcp_exe),
        args=args,
        env=env_vars,
    )

def _is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _start_chrome_remote_debug(port: int, profile_dir: Path) -> None:
    if sys.platform != "win32":  # existing Linux logic already handles non-Windows
        return
    if _is_port_open(port):
        return

    profile_dir.mkdir(parents=True, exist_ok=True)

    chrome_path = os.getenv(
        "SELENIUM_MCP_CHROME_PATH",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    )
    chrome_executable = Path(chrome_path)
    if not chrome_executable.exists():
        fallback = shutil.which("chrome.exe")
        if not fallback:
            LOGGER.warning("Chrome executable not found; start it manually for Selenium MCP.")
            return
        chrome_executable = Path(fallback)

    try:
        subprocess.Popen(
            [
                str(chrome_executable),
                f"--remote-debugging-port={port}",
                f"--user-data-dir={profile_dir}",
                "--profile-directory=Default",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(10):
            if _is_port_open(port):
                break
            time.sleep(1)
        else:
            LOGGER.warning(
                "Chrome launched but remote debugging port %s did not open; Selenium MCP may retry with its own launcher.",
                port,
            )
    except Exception as exc:
        LOGGER.warning("Failed to launch Chrome for Selenium MCP: %s", exc)

def read_test_plan(plan_path: Path) -> str:
    """Load the generated Playwright test plan from disk."""
    if not plan_path.exists():
        raise FileNotFoundError(
            f"Test plan not found at {plan_path}. Generate it before running this agent."
        )
    return plan_path.read_text(encoding="utf-8").strip()


def split_plan_into_suites(plan_markdown: str) -> list[tuple[str, str]]:
    """Break the Markdown plan into per-suite sections."""
    suites: list[tuple[str, str]] = []
    current_name: Optional[str] = None
    current_lines: list[str] = []
    for raw_line in plan_markdown.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            if current_name and current_lines:
                suites.append((current_name, "\n".join(current_lines).strip()))
            current_name = stripped[3:].strip()
            current_lines = [stripped]
        elif current_name:
            if stripped == "---":
                continue
            current_lines.append(raw_line)
    if current_name and current_lines:
        suites.append((current_name, "\n".join(current_lines).strip()))
    return [(name, section) for name, section in suites if section]


def build_execution_prompt(
    plan_markdown: str,
    base_url: str | None = None,
    *,
    suite_markdown: str | None = None,
    suite_name: str | None = None,
    suite_index: Optional[int] = None,
    suite_total: Optional[int] = None,
) -> str:
    """Create the prompt that instructs the agent how to execute the plan."""
    url_directive = ""
    if base_url:
        url_directive = (
            f"The application under test is served at {base_url}. Always load and reload this origin only; "
            "do not probe alternative hosts or ports when scenarios require navigation or reset. "
        )
    scope_directive = ""
    if suite_markdown is not None:
        scope_parts: list[str] = [
            "Execute only the following suite from the broader test plan, completing every scenario in order.",
        ]
        if suite_name:
            scope_parts.insert(0, f"You are running suite '{suite_name}'.")
        if suite_index is not None and suite_total is not None:
            scope_parts.append(
                f"This is suite {suite_index} of {suite_total}; defer other suites because they will be handled separately."
            )
        scope_directive = " ".join(scope_parts) + " "
    plan_body = plan_markdown if suite_markdown is None else f"# Playwright Test Plan\n\n{suite_markdown}"
    return (
        "You are a QA automation executor. You receive a Playwright test plan in Markdown. "
        "For each suite and scenario, translate the intent into concrete Playwright test steps. "
        "Use the Playwright MCP tool to run the necessary tests against the target application. "
        f"{url_directive}{scope_directive}"
        "Report consolidated pass/fail results, notable logs, and any follow-up actions.\n\n"
        "Playwright Test Plan:\n\n"
        f"{plan_body}"
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


def summarize_execution_output(output: str, plan_markdown: str | None = None) -> str:
    """Create a structured summary of the MCP execution output."""
    if not output.strip():
        return "No output was produced by PlaywrightRunnerAgent."

    normalized_output = output.replace("\r\n", "\n")

    def sanitize_heading(text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text.strip())
        cleaned = cleaned.strip("* ")
        return cleaned

    def parse_plan(markdown: str) -> OrderedDict[str, list[str]]:
        suites = OrderedDict()
        current_suite: Optional[str] = None
        for raw_line in markdown.splitlines():
            stripped = raw_line.strip()
            if stripped.startswith("## "):
                suite_name = sanitize_heading(stripped[3:])
                current_suite = suite_name or "General"
                suites.setdefault(current_suite, [])
                continue
            if stripped.startswith("###"):
                scenario_name = sanitize_heading(stripped.lstrip("#"))
                if not current_suite:
                    current_suite = "General"
                    suites.setdefault(current_suite, [])
                suites[current_suite].append(scenario_name)
        return suites

    def humanize_sentence(sentence: str) -> str:
        text = re.sub(r"\s+", " ", sentence.strip().rstrip(":"))
        if not text:
            return ""
        lowered = text.lower()
        replacements = [
            ("let me ", "Attempted to "),
            ("i'll ", "Planned to "),
            ("i notice ", "Observation: "),
            ("it appears ", "Observation: "),
            ("perfect!", "Outcome:"),
        ]
        for trigger, repl in replacements:
            if lowered.startswith(trigger):
                text = repl + text[len(trigger):].lstrip()
                break
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        if len(text) > 250:
            text = text[:247].rstrip() + "…"
        return text

    def extract_bullets(segment: str) -> list[str]:
        cleaned_segment = segment.strip()
        if not cleaned_segment:
            return []
        raw_lines = [line.strip() for line in cleaned_segment.splitlines() if line.strip()]
        if not raw_lines:
            raw_lines = [cleaned_segment]
        fragments: list[str] = []
        for raw_line in raw_lines:
            if raw_line.startswith("##") or raw_line.startswith("###"):
                continue
            if raw_line.lower().startswith("summary saved to"):
                continue
            normalized = re.sub(r"\s+", " ", raw_line)
            pieces = re.split(r"(?<=[\.\?\!])\s+(?=[A-Z])", normalized)
            if not pieces:
                pieces = [normalized]
            for piece in pieces:
                fragments.append(piece.strip())

        bullets: list[str] = []
        seen: set[str] = set()
        for fragment in fragments:
            sentence = humanize_sentence(fragment)
            if not sentence:
                continue
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            bullets.append(f"- {sentence}")
        return bullets[:5]

    plan_structure = parse_plan(plan_markdown) if plan_markdown else OrderedDict()

    summary_data: OrderedDict[str, OrderedDict[str, list[str]]] = OrderedDict()
    summary_data["General"] = OrderedDict()
    summary_data["General"]["Overview"] = []

    if plan_structure:
        for suite_name, scenarios in plan_structure.items():
            summary_data.setdefault(suite_name, OrderedDict())
            for scenario_name in scenarios:
                summary_data[suite_name][scenario_name] = []

    lower_output = normalized_output.lower()

    def locate_positions(phrases: list[str]) -> list[tuple[int, int, str]]:
        positions: list[tuple[int, int, str]] = []
        search_start = 0
        for phrase in phrases:
            target = phrase.lower()
            idx = lower_output.find(target, search_start)
            if idx == -1:
                idx = lower_output.find(target)
            if idx == -1:
                continue
            positions.append((idx, idx + len(phrase), phrase))
            search_start = idx + len(phrase)
        return sorted(positions, key=lambda item: item[0])

    suite_positions = locate_positions(list(plan_structure.keys())) if plan_structure else []

    if suite_positions:
        first_suite_start = suite_positions[0][0]
        general_segment = normalized_output[:first_suite_start].strip()
        general_bullets = extract_bullets(general_segment)
        if general_bullets:
            summary_data["General"]["Overview"].extend(general_bullets)
    else:
        general_bullets = extract_bullets(normalized_output)
        if general_bullets:
            summary_data["General"]["Overview"].extend(general_bullets)

    scenario_entries: list[tuple[Optional[int], Optional[int], str, str]] = []
    if plan_structure:
        search_cursor = 0
        scenario_order: list[tuple[str, str]] = [
            (suite, scenario) for suite, scenarios in plan_structure.items() for scenario in scenarios
        ]
        for suite_name, scenario_name in scenario_order:
            target = scenario_name.lower()
            idx = lower_output.find(target, search_cursor)
            if idx == -1:
                idx = lower_output.find(target)
            if idx == -1:
                scenario_entries.append((None, None, suite_name, scenario_name))
                continue
            scenario_entries.append((idx, idx + len(scenario_name), suite_name, scenario_name))
            search_cursor = idx + len(scenario_name)

    suite_boundaries = [pos for pos, _, _ in suite_positions]

    for index, (start, end, suite_name, scenario_name) in enumerate(scenario_entries):
        if start is None or end is None:
            continue
        boundary_candidates: list[int] = []
        for next_index in range(index + 1, len(scenario_entries)):
            next_start = scenario_entries[next_index][0]
            if next_start is not None:
                boundary_candidates.append(next_start)
                break
        for suite_start in suite_boundaries:
            if suite_start > end:
                boundary_candidates.append(suite_start)
                break
        segment_end = min(boundary_candidates) if boundary_candidates else len(normalized_output)
        segment_text = normalized_output[end:segment_end]
        segment_text = segment_text.lstrip(" *#:-\n\r\t")
        bullets = extract_bullets(segment_text)
        if bullets:
            summary_data.setdefault(suite_name, OrderedDict())
            summary_data[suite_name].setdefault(scenario_name, [])
            summary_data[suite_name][scenario_name].extend(bullets)

    if not summary_data["General"]["Overview"]:
        summary_data.pop("General")

    summary_lines = ["# Playwright MCP Test Summary", ""]

    for suite_name, scenarios in summary_data.items():
        summary_lines.append(f"## {suite_name}")
        for scenario_name, entries in scenarios.items():
            summary_lines.append(f"### {scenario_name}")
            if not entries:
                summary_lines.append("- (no details captured)")
            else:
                summary_lines.extend(entries)
            summary_lines.append("")
        summary_lines.append("")

    summary = "\n".join(summary_lines).strip()
    return summary + "\n"


async def run_playwright_test_agent(
    plan_path: Path,
    *,
    echo: bool = False,
    start_server: bool = True,
    server_command: Optional[list[str]] = None,
    server_cwd: Optional[Path] = None,
    base_url: Optional[str] = DEFAULT_BASE_URL,
    log_path: Optional[Path] = None,
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
    suite_sections = split_plan_into_suites(plan_markdown)
    suite_total = len(suite_sections) if suite_sections else 1
    try:
        relative_plan = plan_path.relative_to(PROJECT_ROOT)
        plan_display_path = relative_plan.as_posix()
    except ValueError:
        plan_display_path = plan_path.as_posix()
    metrics_collector = AgentRunMetricsCollector(
        plan_path=plan_display_path,
        base_url=base_url,
        suite_total=suite_total,
    )
    prompt = build_execution_prompt(plan_markdown, base_url)

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
    if base_url:
        instructions += (
            f" The application is hosted at {base_url}; stay on this origin for all navigation, "
            "state resets, and reloads."
        )

    transcript = []

    log_target = log_path or DEFAULT_LOG_PATH
    resolved_log = log_target if log_target.is_absolute() else (PROJECT_ROOT / log_target).resolve()
    resolved_log.parent.mkdir(parents=True, exist_ok=True)
    log_file_handle = resolved_log.open("w", encoding="utf-8")
    metrics_path = resolved_log.with_suffix(".metrics.json")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_file_handle.write(f"# Playwright Test Run\nStarted: {timestamp}\nPlan: {plan_path}\n\n")

    agent_kwargs = {
        "name": "PlaywrightRunnerAgent",
        "instructions": instructions,
        "tools": [create_playwright_mcp_tool()],
        "allow_multiple_tool_calls": True,
    }

    context_manager = client.create_agent(max_output_tokens=60000, **agent_kwargs)

    metrics_data: dict[str, Any] | None = None
    metrics_error: Exception | None = None

    try:
        async with context_manager as agent:
            suites_to_run: list[tuple[Optional[str], Optional[str]]] = (
                [(name, body) for name, body in suite_sections]
                if suite_sections
                else [(None, None)]
            )
            response_updates: list[Any] = []
            if echo:
                print("Agent: ", end="", flush=True)
            for index, (suite_name, suite_body) in enumerate(suites_to_run, start=1):
                suite_prompt = prompt
                if suite_body is not None:
                    suite_prompt = build_execution_prompt(
                        plan_markdown,
                        base_url,
                        suite_markdown=suite_body,
                        suite_name=suite_name,
                        suite_index=index,
                        suite_total=len(suites_to_run),
                    )
                thread = agent.get_new_thread()
                suite_updates: list[Any] = []
                metrics_collector.start_suite(suite_name, index)
                try:
                    async for chunk in agent.run_stream(suite_prompt, thread=thread):
                        suite_updates.append(chunk)
                        if chunk.text:
                            transcript.append(chunk.text)
                            log_file_handle.write(chunk.text)
                            log_file_handle.flush()
                            if echo:
                                print(chunk.text, end="", flush=True)
                        metrics_collector.record_update(chunk)
                except Exception:
                    metrics_collector.abort_active_suite()
                    raise
                response_updates.extend(suite_updates)
                metrics_collector.finish_suite()
                if suite_updates and index < len(suites_to_run):
                    transcript.append("\n")
                    log_file_handle.write("\n")
                    log_file_handle.flush()
                if echo and index < len(suites_to_run):
                    print()
            if echo:
                print()
            log_agent_stream_metadata(
                "PlaywrightRunnerAgent",
                response_updates,
                logger=LOGGER,
            )
        metrics_data = metrics_collector.finalize_run()
    except Exception as exc:
        metrics_error = exc
        metrics_collector.abort_active_suite()
    finally:
        log_file_handle.write("\n")
        log_file_handle.flush()
        log_file_handle.close()
        if start_server and server_process is not None:
            stop_local_server(server_process)

    output_text = "".join(transcript).strip()
    summary_text = summarize_execution_output(output_text, plan_markdown)

    if metrics_data is None:
        try:
            metrics_data = metrics_collector.finalize_run()
        except RuntimeError as exc:
            LOGGER.warning("Unable to finalize metrics: %s", exc)
            metrics_collector.abort_active_suite()
            metrics_data = {
                "run": {
                    "plan_path": plan_display_path,
                    "base_url": base_url,
                    "suite_total": suite_total,
                },
                "suites": metrics_collector.completed_suites,
            }
    if metrics_error:
        run_section = metrics_data.setdefault("run", {}) if isinstance(metrics_data, dict) else None
        if isinstance(run_section, dict):
            run_section.setdefault(
                "error",
                f"{metrics_error.__class__.__name__}: {metrics_error}",
            )
    dump_metrics_to_file(metrics_data, metrics_path)

    if metrics_error:
        summary_text = summary_text.rstrip() + f"\n\nRun terminated with error: {metrics_error}\n"

    with resolved_log.open("a", encoding="utf-8") as summary_file:
        summary_file.write("\n# Summary\n")
        summary_file.write(summary_text)
        summary_file.write("\n")

    result = {
        "plan_path": plan_display_path,
        "output": output_text,
        "output_preview": output_text[:1000],
        "summary_text": summary_text,
        "metrics_path": metrics_path.as_posix(),
    }
    if echo:
        print(f"\nMetrics written to: {metrics_path.as_posix()}")
    if metrics_error:
        raise metrics_error
    return result


@ai_function(
    name="playwright_test_runner",
    description="Executes the generated Playwright test plan using the Playwright MCP server and reports results.",
)
async def run_playwright_tests_tool(
    plan_path: Annotated[Optional[str], Field(description="Path to the Playwright test plan markdown file.")] = None,
    start_host: Annotated[bool, Field(description="Whether to start the local development server before running tests.")] = True,
    base_url: Annotated[Optional[str], Field(description="Explicit base URL for the application under test.")] = None,
) -> Dict[str, Any]:
    resolved_path = Path(plan_path) if plan_path else DEFAULT_TEST_PLAN_PATH
    if not resolved_path.is_absolute():
        resolved_path = (PROJECT_ROOT / resolved_path).resolve()

    resolved_base_url = base_url or DEFAULT_BASE_URL

    result = await run_playwright_test_agent(
        resolved_path,
        echo=False,
        start_server=start_host,
        base_url=resolved_base_url,
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
    parser.add_argument(
        "--base-url",
        type=str,
        default=DEFAULT_BASE_URL,
        help="Base URL for the application under test (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    result = asyncio.run(
        run_playwright_test_agent(
            args.plan,
            echo=True,
            start_server=not args.skip_server,
            base_url=args.base_url,
        )
    )
    if not result["output"]:
        print("No output captured from PlaywrightRunnerAgent.")


if __name__ == "__main__":
    main()
