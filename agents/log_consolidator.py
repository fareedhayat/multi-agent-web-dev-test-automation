import os
import re
import json
from datetime import datetime
from typing import Dict, Any, List


SERVERS = [
    ("playwright_mcp", "Playwright MCP"),
    ("selenium_mcp", "Selenium MCP"),
    ("selenium_server1", "Selenium Server1"),
]


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def split_blocks_by_scenarios(text: str):
    lines = text.splitlines()
    blocks = []
    current_suite = None
    current_block = None
    suite_titles: Dict[str, str] = {}

    # Allow one or more heading hashes (e.g., #, ##, ###) before 'Suite N: Title'
    suite_re = re.compile(r"^#+\s*Suite\s*(\d+)\s*:\s*(.+)")
    # Match variations like `## **Scenario 1.1: Title**`, `## Scenario 1.1: Title`, or `### **Scenario 4.1` etc.
    scen_re = re.compile(r"^\s*(?:#+|)\s*\*{0,2}\s*Scenario\s+(\d+\.\d+)\s*:\s*(.+)")

    def commit_block():
        nonlocal current_block
        if current_block:
            blocks.append(current_block)
            current_block = None

    for line in lines:
        m_suite = suite_re.match(line.strip())
        if m_suite:
            # Starting a new suite; commit any ongoing scenario block
            commit_block()
            suite_num = m_suite.group(1)
            suite_title = m_suite.group(2)
            current_suite = f"Suite {suite_num}: {suite_title}"
            suite_titles[suite_num] = current_suite
            continue

        m_scen = scen_re.match(line.strip())
        if m_scen:
            # Commit previous scenario block
            commit_block()
            scen_id = m_scen.group(1).strip()
            title = m_scen.group(2).strip().rstrip("* ")
            # Prefer suite inferred from scenario id if header missing/mismatched
            scen_suite_num = scen_id.split(".")[0]
            preferred_suite = current_suite
            if scen_suite_num:
                # If current suite is absent or mismatched, fix it
                cur_num = None
                if preferred_suite:
                    mm = re.search(r"Suite\s+(\d+)", preferred_suite)
                    cur_num = mm.group(1) if mm else None
                if (not preferred_suite) or (cur_num and cur_num != scen_suite_num):
                    preferred_suite = suite_titles.get(scen_suite_num, f"Suite {scen_suite_num}")
            current_block = {
                "suite": preferred_suite,
                "id": scen_id,
                "title": title,
                "lines": [line],
            }
            continue

        # Accumulate lines inside the current scenario block
        if current_block:
            current_block["lines"].append(line)

    # Final commit
    commit_block()
    return blocks


def classify_status_from_lines(lines):
    # Heuristic classification based on presence of common tokens
    text = "\n".join(lines)
    status_line = None

    # Try to find an explicit results/status line first
    for ln in lines:
        if re.search(r"\b(Result|Results|Status)\b", ln, re.IGNORECASE):
            status_line = ln.strip()
            break

    def has_token(token):
        return any(token in ln for ln in lines) or (token in text)

    def has_word(word):
        return re.search(fr"\b{word}\b", text, re.IGNORECASE) is not None

    status = "UNKNOWN"
    if has_token("❌") or has_word("FAIL"):
        status = "FAIL"
    elif has_token("⚠️") or has_word("PARTIAL"):
        status = "PARTIAL"
    elif has_token("✅") or has_word("PASS"):
        status = "PASS"

    # Notes: take a few informative lines (bullets or concise sentences)
    notes = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith(("- ", "• ", "**", "Passed:", "Failed:", "Issues:", "Observations:", "Note:")):
            notes.append(s)
        # keep it short
        if len(notes) >= 6:
            break

    return status, status_line, notes


def parse_log(path: str):
    text = read_text(path)
    blocks = split_blocks_by_scenarios(text)
    scenarios = []
    for blk in blocks:
        status, status_line, notes = classify_status_from_lines(blk["lines"]) 
        scenarios.append({
            "suite": blk.get("suite"),
            "id": blk.get("id"),
            "title": blk.get("title"),
            "status": status,
            "status_text": status_line,
            "notes": notes,
        })
    return scenarios


def _try_get(d: Dict[str, Any], keys: List[str], default=None):
    for k in keys:
        if isinstance(d, dict) and k in d:
            return d[k]
    return default


def _parse_suite_number_from_name(name: str) -> str:
    if not name:
        return None
    m = re.search(r"Suite\s+(\d+)", name)
    if m:
        return m.group(1)
    return None


def parse_summary(summary_path: str) -> Dict[str, Dict[str, Any]]:
    """Return metrics keyed by suite number as string: { '1': {duration_seconds, input_tokens, output_tokens} }"""
    if not os.path.exists(summary_path):
        return {}
    try:
        with open(summary_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
    except Exception:
        return {}

    metrics_by_suite: Dict[str, Dict[str, Any]] = {}

    # Common patterns: top-level 'suites' list with objects
    suites = _try_get(data, ["suites", "per_suites", "suite_metrics", "suiteList"], default=[])
    if isinstance(suites, list) and suites:
        for s in suites:
            # Determine suite id/number
            suite_name = _try_get(s, ["name", "suite", "title"], None)
            num = _try_get(s, ["index", "number", "id"], None)
            if isinstance(num, int):
                suite_num = str(num)
            else:
                suite_num = _parse_suite_number_from_name(str(suite_name)) if suite_name else None

            if not suite_num:
                # try parse from nested
                suite_num = _parse_suite_number_from_name(json.dumps(s))

            # Extract metrics
            duration = _try_get(s, ["duration_seconds", "seconds", "duration"], None)
            usage = _try_get(s, ["usage", "tokens"], {}) or {}
            in_tok = _try_get(usage, ["input_token_count", "input_tokens", "input"], None)
            out_tok = _try_get(usage, ["output_token_count", "output_tokens", "output"], None)

            if suite_num:
                metrics_by_suite[suite_num] = {
                    "duration_seconds": duration,
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                }

    return metrics_by_suite


def consolidate(workspace_root: str):
    artifacts_dir = os.path.join(workspace_root, "artifacts")
    server_logs: Dict[str, List[Dict[str, Any]]] = {}
    server_suite_metrics: Dict[str, Dict[str, Any]] = {}
    server_suite_tokens: Dict[str, Dict[str, Any]] = {}

    def parse_metrics_tokens(metrics_path: str) -> Dict[str, Dict[str, Any]]:
        """Parse suite-level token usage from run.metrics.json if present.
        Returns mapping: { '1': {'input_tokens': int|None, 'output_tokens': int|None}, ... }
        """
        if not os.path.exists(metrics_path):
            return {}
        try:
            with open(metrics_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
        except Exception:
            return {}

        tokens_by_suite: Dict[str, Dict[str, Any]] = {}

        # Heuristic: look for per-suite entries that include a 'usage' object
        def extract_from_suites(suites_list):
            if isinstance(suites_list, list):
                for s in suites_list:
                    usage = s.get("usage") if isinstance(s, dict) else None
                    if isinstance(usage, dict):
                        in_tok = usage.get("input_token_count") or usage.get("input_tokens") or usage.get("input")
                        out_tok = usage.get("output_token_count") or usage.get("output_tokens") or usage.get("output")
                        # derive suite number
                        suite_name = s.get("suite_name") or s.get("name") or s.get("suite") or s.get("title")
                        num = s.get("suite_index") or s.get("index") or s.get("number") or s.get("id")
                        if isinstance(num, int):
                            suite_num = str(num)
                        else:
                            suite_num = _parse_suite_number_from_name(str(suite_name)) if suite_name else None
                        if suite_num:
                            tokens_by_suite.setdefault(suite_num, {})
                            if in_tok is not None:
                                tokens_by_suite[suite_num]["input_tokens"] = in_tok
                            if out_tok is not None:
                                tokens_by_suite[suite_num]["output_tokens"] = out_tok

        # Common top-level keys that could contain suites
        for key in ("suites", "suite_runs", "per_suites", "suiteList"):
            suites_list = data.get(key)
            extract_from_suites(suites_list)

        return tokens_by_suite
    for folder, label in SERVERS:
        log_path = os.path.join(artifacts_dir, folder, "run.log")
        summary_path = os.path.join(artifacts_dir, folder, "run.summary.json")
        metrics_path = os.path.join(artifacts_dir, folder, "run.metrics.json")
        if not os.path.exists(log_path):
            server_logs[folder] = []
        else:
            server_logs[folder] = parse_log(log_path)
        server_suite_metrics[folder] = parse_summary(summary_path)
        server_suite_tokens[folder] = parse_metrics_tokens(metrics_path)

    # Consolidate by scenario id
    scenarios_by_id = {}
    for folder, label in SERVERS:
        for s in server_logs.get(folder, []):
            sid = s.get("id") or "UNKNOWN"
            if sid not in scenarios_by_id:
                scenarios_by_id[sid] = {
                    "id": sid,
                    "title": s.get("title"),
                    "suite": s.get("suite"),
                    "servers": {}
                }
            entry = scenarios_by_id[sid]
            # Prefer first encountered non-empty title/suite
            if not entry.get("title") and s.get("title"):
                entry["title"] = s.get("title")
            if not entry.get("suite") and s.get("suite"):
                entry["suite"] = s.get("suite")
            # Determine suite number from suite string
            suite_str = s.get("suite") or ""
            m = re.search(r"Suite\s+(\d+)", suite_str)
            suite_num = m.group(1) if m else None
            sm = server_suite_metrics.get(folder, {})
            sm_for_suite = sm.get(suite_num or "", {}) if sm else {}

            # Keep metrics in-memory for Markdown only; JSON will omit these per-scenario metrics
            entry["servers"][folder] = {
                "label": dict(SERVERS).get(folder, folder),
                "status": s.get("status"),
                "status_text": s.get("status_text"),
                "notes": s.get("notes") or [],
                "metrics": {
                    "suite_duration_seconds": sm_for_suite.get("duration_seconds"),
                    "suite_input_tokens": sm_for_suite.get("input_tokens"),
                    "suite_output_tokens": sm_for_suite.get("output_tokens"),
                }
            }

    consolidated = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "scenarios": sorted(
            scenarios_by_id.values(),
            key=lambda x: (
                tuple(map(int, x["id"].split("."))) if re.match(r"^\d+\.\d+$", x["id"] or "") else (9999, 9999)
            )
        )
    }

    # Compute per-server per-suite scenario counts to allow optional "estimated per case" metrics
    per_server_suite_counts: Dict[str, Dict[str, int]] = {k: {} for k, _ in SERVERS}
    for sc in consolidated["scenarios"]:
        suite_str = sc.get("suite") or ""
        m = re.search(r"Suite\s+(\d+)", suite_str)
        suite_num = m.group(1) if m else None
        if not suite_num:
            continue
        for folder, _ in SERVERS:
            if sc["servers"].get(folder):
                per_server_suite_counts[folder][suite_num] = per_server_suite_counts[folder].get(suite_num, 0) + 1

    # Add estimated per-case fields
    for sc in consolidated["scenarios"]:
        suite_str = sc.get("suite") or ""
        m = re.search(r"Suite\s+(\d+)", suite_str)
        suite_num = m.group(1) if m else None
        for folder, _ in SERVERS:
            sv = sc["servers"].get(folder)
            if not sv:
                continue
            metrics = sv.get("metrics") or {}
            count = per_server_suite_counts.get(folder, {}).get(suite_num or "", 0)
            if count and metrics:
                dur = metrics.get("suite_duration_seconds") or 0
                it = metrics.get("suite_input_tokens") or 0
                ot = metrics.get("suite_output_tokens") or 0
                # Provide simple even split estimation
                metrics["estimated_case_duration_seconds"] = (dur / count) if dur else None
                metrics["estimated_case_input_tokens"] = (it // count) if it else None
                metrics["estimated_case_output_tokens"] = (ot // count) if ot else None

    # Write outputs
    out_dir = os.path.join(artifacts_dir, "comparison")
    os.makedirs(out_dir, exist_ok=True)

    json_path = os.path.join(out_dir, "consolidated_logs.json")
    # Build suite totals for JSON output (tokens non-null at suite level)
    # Determine suites in numeric order based on parsed suite number
    suites_map: Dict[str, str] = {}
    for sc in consolidated["scenarios"]:
        suite_str = sc.get("suite") or "(Unknown Suite)"
        m = re.search(r"Suite\s+(\d+)", suite_str or "")
        suite_num = m.group(1) if m else None
        if suite_num and suite_num not in suites_map:
            suites_map[suite_num] = suite_str
    suites_order_nums = sorted(suites_map.keys(), key=lambda x: int(x))

    suite_totals_list: List[Dict[str, Any]] = []
    for suite_num in suites_order_nums:
        suite_str = suites_map[suite_num]
        servers_totals: Dict[str, Any] = {}
        for folder, label in SERVERS:
            # Duration from summary
            dur = None
            sm = server_suite_metrics.get(folder, {})
            if suite_num and sm.get(suite_num):
                dur = sm[suite_num].get("duration_seconds")
            # Tokens from metrics
            toks = server_suite_tokens.get(folder, {}).get(suite_num or "", {})
            in_tok = toks.get("input_tokens")
            out_tok = toks.get("output_tokens")
            servers_totals[folder] = {
                "label": label,
                "duration_seconds": dur,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
            }
        suite_totals_list.append({
            "suite": suite_str,
            "servers": servers_totals
        })

    scenarios_for_json: List[Dict[str, Any]] = []
    for sc in consolidated["scenarios"]:
        sc_copy = {
            "id": sc.get("id"),
            "title": sc.get("title"),
            "suite": sc.get("suite"),
            "servers": {}
        }
        for folder, _ in SERVERS:
            sv = sc["servers"].get(folder)
            if not sv:
                continue
            sv_copy = {
                "label": sv.get("label"),
                "status": sv.get("status"),
                "status_text": sv.get("status_text"),
                "notes": sv.get("notes") or []
            }
            sc_copy["servers"][folder] = sv_copy
        scenarios_for_json.append(sc_copy)

    consolidated_json = {
        "generated_at": consolidated["generated_at"],
        "scenarios": scenarios_for_json,
        "suite_totals": suite_totals_list
    }

    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(consolidated_json, jf, indent=2, ensure_ascii=False)

    md_path = os.path.join(out_dir, "consolidated_logs.md")
    with open(md_path, "w", encoding="utf-8") as mf:
        mf.write("# Consolidated Test Case Results\n\n")
        mf.write(f"Generated at: {consolidated['generated_at']}\n\n")

        # Group scenarios by suite string to add suite-level totals at the end
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        suite_num_name: Dict[str, str] = {}
        for sc in consolidated["scenarios"]:
            suite_str = sc.get("suite") or "(Unknown Suite)"
            m = re.search(r"Suite\s+(\d+)", suite_str or "")
            suite_num = m.group(1) if m else None
            if not suite_num:
                # Skip scenarios that don't map to a numbered suite
                continue
            if suite_str not in grouped:
                grouped[suite_str] = []
                suite_num_name[suite_num] = suite_str
            grouped[suite_str].append(sc)

        # Sort suites by numeric suite number
        ordered_suite_nums = sorted(suite_num_name.keys(), key=lambda x: int(x))
        for suite_num in ordered_suite_nums:
            suite_str = suite_num_name[suite_num]
            mf.write(f"# {suite_str}\n\n")
            for sc in grouped[suite_str]:
                mf.write(f"## Scenario {sc['id']}: {sc.get('title') or ''}\n")
                for folder, label in SERVERS:
                    sv = sc["servers"].get(folder)
                    if not sv:
                        mf.write(f"- {label}: No data\n")
                        continue
                    mf.write(f"- {label}: {sv.get('status') or 'UNKNOWN'}\n")
                    if sv.get("status_text"):
                        mf.write(f"  - {sv['status_text']}\n")
                    notes = sv.get("notes") or []
                    for n in notes[:4]:
                        mf.write(f"  - {n}\n")
                    # Omit per-scenario estimated metrics from Markdown per user request
                mf.write("\n")

            # Suite totals per server (duration from summary, tokens from metrics)
            mf.write("### Suite Totals\n")
            # Extract suite number from string
            # suite_num already known from loop
            for folder, label in SERVERS:
                # Duration from summary parse
                dur = None
                sm = server_suite_metrics.get(folder, {})
                if suite_num and sm.get(suite_num):
                    dur = sm[suite_num].get("duration_seconds")
                # Tokens from metrics parse
                toks = server_suite_tokens.get(folder, {}).get(suite_num or "", {})
                in_tok = toks.get("input_tokens")
                out_tok = toks.get("output_tokens")
                parts = []
                if dur is not None:
                    parts.append(f"time={dur:.2f}s")
                if in_tok is not None:
                    parts.append(f"in_tokens={in_tok}")
                if out_tok is not None:
                    parts.append(f"out_tokens={out_tok}")
                if parts:
                    mf.write(f"- {label}: "+", ".join(parts)+"\n")
                else:
                    mf.write(f"- {label}: No suite totals available\n")
            mf.write("\n")

    return json_path, md_path


def main():
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    json_path, md_path = consolidate(workspace_root)
    print("Consolidation complete.")
    print("JSON:", json_path)
    print("MD:", md_path)


if __name__ == "__main__":
    main()
