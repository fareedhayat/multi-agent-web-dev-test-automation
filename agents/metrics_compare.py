import json
import os
from collections import Counter
from statistics import mean
from typing import Any, Dict, List


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_kpis(name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    run = data.get("run", {})
    suites: List[Dict[str, Any]] = data.get("suites", [])

    runtime = run.get("duration_seconds", 0) or 0
    usage = run.get("usage", {})
    input_tokens = usage.get("input_token_count", 0) or 0
    output_tokens = usage.get("output_token_count", 0) or 0

    tokens_per_second = (input_tokens / runtime) if runtime else None
    output_per_input = (output_tokens / input_tokens) if input_tokens else None

    suite_total = run.get("suite_total") or len(suites)
    suite_durations = [s.get("duration_seconds", 0) or 0 for s in suites]
    avg_suite_duration = (sum(suite_durations) / len(suite_durations)) if suite_durations else None

    # Aggregate tool call stats
    tool_calls: List[Dict[str, Any]] = []
    for s in suites:
        tool_calls.extend(s.get("tool_calls", []))

    tool_count_total = len(tool_calls)
    errors_count = sum(1 for t in tool_calls if t.get("error", False))
    tool_name_counts = Counter(t.get("tool_name") for t in tool_calls if t.get("tool_name"))
    avg_tool_duration = mean([t.get("duration_seconds", 0) or 0 for t in tool_calls]) if tool_calls else None

    return {
        "name": name,
        "runtime_seconds": runtime,
        "suite_total": suite_total,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tokens_per_second": tokens_per_second,
        "output_per_input": output_per_input,
        "avg_suite_duration": avg_suite_duration,
        "tool_calls_total": tool_count_total,
        "tool_errors": errors_count,
        "top_tools": tool_name_counts.most_common(10),
        "avg_tool_duration": avg_tool_duration,
    }


def main() -> None:
    base = os.path.dirname(os.path.dirname(__file__))
    metrics_paths = {
        "Playwright MCP": os.path.join(base, "artifacts", "playwright_mcp", "run.metrics.json"),
        "Selenium MCP (Angie)": os.path.join(base, "artifacts", "selenium_mcp", "run.metrics.json"),
        "Selenium Server1": os.path.join(base, "artifacts", "selenium_server1", "run.metrics.json"),
    }

    results: List[Dict[str, Any]] = []
    missing: List[str] = []

    for name, path in metrics_paths.items():
        if not os.path.exists(path):
            missing.append(f"{name} → {path}")
            continue
        data = load_json(path)
        kpis = compute_kpis(name, data)
        results.append(kpis)

    output_dir = os.path.join(base, "artifacts", "comparison")
    os.makedirs(output_dir, exist_ok=True)

    # Write JSON comparison
    output_json = os.path.join(output_dir, "run.comparison.json")
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({"comparisons": results, "missing": missing}, f, indent=2)

    # Write a concise Markdown summary (no screenshots)
    output_md = os.path.join(output_dir, "run.comparison.md")
    lines: List[str] = []
    lines.append("# MCP Comparison (Runtime, Tokens, Tools)\n")
    for r in results:
        lines.append(f"## {r['name']}")
        lines.append(f"- Runtime: {r['runtime_seconds']:.2f}s")
        lines.append(f"- Input tokens: {r['input_tokens']:,}")
        lines.append(f"- Output tokens: {r['output_tokens']:,}")
        if r['tokens_per_second'] is not None:
            lines.append(f"- Tokens/sec: {r['tokens_per_second']:.2f}")
        if r['output_per_input'] is not None:
            lines.append(f"- Output/Input ratio: {r['output_per_input']:.6f}")
        if r['avg_suite_duration'] is not None:
            lines.append(f"- Avg suite duration: {r['avg_suite_duration']:.2f}s")
        lines.append(f"- Tool calls: {r['tool_calls_total']}")
        lines.append(f"- Tool errors: {r['tool_errors']}")
        if r['avg_tool_duration'] is not None:
            lines.append(f"- Avg tool duration: {r['avg_tool_duration']:.2f}s")
        if r['top_tools']:
            top = ", ".join([f"{name}({count})" for name, count in r['top_tools']])
            lines.append(f"- Top tools: {top}")
        lines.append("")

    if missing:
        lines.append("## Missing")
        for m in missing:
            lines.append(f"- {m}")

    with open(output_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote: {output_json}")
    print(f"Wrote: {output_md}")
    if missing:
        print("Missing metrics files:")
        for m in missing:
            print(f"- {m}")


if __name__ == "__main__":
    main()
