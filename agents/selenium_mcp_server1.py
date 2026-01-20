"""Thin wrapper to run the first Selenium MCP server runner.
Loads and executes `playwright_test_runner.py` main without relying on package imports,
so it can be invoked via `python agents/selenium_mcp_server1.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path
import importlib.util


def _run_main() -> None:
    module_path = Path(__file__).resolve().parent / "playwright_test_runner.py"
    spec = importlib.util.spec_from_file_location("selenium_server1_runner", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load playwright_test_runner module spec")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    if hasattr(mod, "main"):
        mod.main()
    else:
        raise RuntimeError("playwright_test_runner.main not found")


if __name__ == "__main__":
    _run_main()
