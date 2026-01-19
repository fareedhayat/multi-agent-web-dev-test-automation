"""Utilities for capturing structured metrics from agent streaming runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
import time
import os
import json

from agent_framework import (
    AgentResponse,
    AgentResponseUpdate,
    FunctionCallContent,
    FunctionResultContent,
    MCPServerToolCallContent,
    MCPServerToolResultContent,
    UsageDetails,
)

_MAX_STRING_PREVIEW = 1024


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _truncate_string(value: str, limit: int = _MAX_STRING_PREVIEW) -> str:
    if len(value) <= limit:
        return value
    omitted = len(value) - limit
    return f"{value[:limit]}... (+{omitted} chars truncated)"


def _safe_serialize(value: Any, *, limit: int = _MAX_STRING_PREVIEW) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return _truncate_string(value, limit)
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, (bytes, bytearray)):
        return f"<binary {len(value)} bytes>"
    if isinstance(value, dict):
        return {str(key): _safe_serialize(val, limit=limit) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_serialize(item, limit=limit) for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return value.to_dict(exclude_none=True)
        except Exception:
            return repr(value)
    if hasattr(value, "model_dump") and callable(value.model_dump):
        try:
            return value.model_dump(exclude_none=True)
        except Exception:
            return repr(value)
    try:
        return repr(value)
    except Exception:
        return "<unserializable>"


def _extract_base64_length(value: Any) -> int:
    """Best-effort detection of base64-encoded image content length.

    - If a data URI string (e.g., "data:image/png;base64,<...>") is present, returns the length
      of the base64 payload after "base64,".
    - If a standalone base64 string is present, returns its string length.
    - Recurses through dicts/lists to find any embedded base64 strings.
    """
    try:
        if value is None:
            return 0
        if isinstance(value, str):
            s = value.strip()
            # Data URI pattern
            idx = s.find("base64,")
            if idx != -1:
                return len(s[idx + len("base64,"):])
            # Fallback: treat long strings with base64-like charset as base64 payload
            # (heuristic; won't be perfect, but good enough for estimates)
            # Base64 valid chars set + padding '='
            b64_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
            if len(s) > 64 and all(c in b64_chars for c in s[-64:]):
                return len(s)
            return 0
        if isinstance(value, dict):
            total = 0
            for v in value.values():
                total += _extract_base64_length(v)
            return total
        if isinstance(value, (list, tuple, set)):
            total = 0
            for v in value:
                total += _extract_base64_length(v)
            return total
    except Exception:
        return 0
    return 0


def _estimate_bytes_from_pathlike(value: Any) -> int:
    """Return total size in bytes for any filesystem paths found in value.

    Recognizes keys commonly used for screenshots like 'path', 'screenshot_path', 'file', 'filepath'.
    Accepts strings or dicts/lists containing those.
    """
    def _size_for_path(p: str) -> int:
        try:
            if not p:
                return 0
            # Expanduser/envvars and normalize
            p_norm = os.path.expandvars(os.path.expanduser(p))
            path = Path(p_norm)
            if path.is_file():
                return path.stat().st_size
        except Exception:
            return 0
        return 0

    try:
        if value is None:
            return 0
        if isinstance(value, str):
            return _size_for_path(value)
        if isinstance(value, dict):
            total = 0
            for k, v in value.items():
                key = str(k).lower()
                if key in {"path", "screenshot_path", "file", "filepath"} and isinstance(v, str):
                    total += _size_for_path(v)
                else:
                    total += _estimate_bytes_from_pathlike(v)
            return total
        if isinstance(value, (list, tuple, set)):
            total = 0
            for v in value:
                total += _estimate_bytes_from_pathlike(v)
            return total
    except Exception:
        return 0
    return 0


def _usage_to_dict(usage: Optional[UsageDetails]) -> Optional[Dict[str, Any]]:
    if not usage:
        return None
    try:
        return usage.to_dict(exclude_none=True)
    except Exception:
        return {
            "input_token_count": usage.input_token_count,
            "output_token_count": usage.output_token_count,
            "total_token_count": usage.total_token_count,
            "additional_counts": dict(usage.additional_counts),
        }


@dataclass
class _ToolCallState:
    call_id: str
    name: Optional[str] = None
    server_name: Optional[str] = None
    started_at: Optional[datetime] = None
    started_perf: Optional[float] = None
    completed_at: Optional[datetime] = None
    completed_perf: Optional[float] = None
    argument_fragments: List[Any] = field(default_factory=list)
    output_fragments: List[Any] = field(default_factory=list)
    error: bool = False

    def record_start(self) -> None:
        if self.started_at is None:
            self.started_at = _utc_now()
            self.started_perf = time.perf_counter()

    def record_completion(self) -> None:
        self.completed_at = _utc_now()
        self.completed_perf = time.perf_counter()

    def to_dict(self) -> Dict[str, Any]:
        duration: Optional[float] = None
        if self.started_perf is not None and self.completed_perf is not None:
            duration = max(self.completed_perf - self.started_perf, 0.0)
        return {
            "call_id": self.call_id,
            "tool_name": self.name,
            "server_name": self.server_name,
            "started_at": _to_iso(self.started_at),
            "completed_at": _to_iso(self.completed_at),
            "duration_seconds": duration,
            "arguments": _safe_serialize(self.argument_fragments) if self.argument_fragments else None,
            "output": _safe_serialize(self.output_fragments) if self.output_fragments else None,
            "error": self.error,
        }


@dataclass
class SuiteMetricRecord:
    suite_name: Optional[str]
    suite_index: int
    suite_total: int
    started_at: datetime
    started_perf: float
    updates: List[AgentResponseUpdate] = field(default_factory=list)
    stream_events: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: Dict[str, _ToolCallState] = field(default_factory=dict)
    total_text_chars: int = 0
    # Screenshot accounting
    screenshot_calls_count: int = 0
    screenshot_base64_chars_total: int = 0
    screenshot_bytes_total: int = 0

    def append_update(self, update: AgentResponseUpdate, *, received_at: datetime, perf_timestamp: float) -> None:
        self.updates.append(update)
        text = getattr(update, "text", None)
        if isinstance(text, str):
            self.total_text_chars += len(text)
        event: Dict[str, Any] = {
            "ordinal": len(self.updates),
            "received_at": _to_iso(received_at),
            "text": _safe_serialize(text) if text else None,
            "content_types": [],
            "finish_reason": _safe_serialize(getattr(update, "finish_reason", None)),
            "additional_properties": _safe_serialize(getattr(update, "additional_properties", None)),
        }
        content_types: List[str] = []
        contents: Sequence[Any] = getattr(update, "contents", []) or []
        for content in contents:
            content_type = getattr(content, "type", content.__class__.__name__)
            content_types.append(content_type)
            self._inspect_tool_content(content, perf_timestamp)
            if content_type == "usage":
                event.setdefault("usage_details", []).append(
                    _usage_to_dict(getattr(content, "details", None))
                )
        if content_types:
            event["content_types"] = sorted(dict.fromkeys(content_types))
        else:
            event.pop("content_types", None)
        self.stream_events.append(event)

    def _ensure_tool_state(self, call_id: str) -> _ToolCallState:
        state = self.tool_calls.get(call_id)
        if not state:
            state = _ToolCallState(call_id=call_id)
            self.tool_calls[call_id] = state
        return state

    def _inspect_tool_content(self, content: Any, perf_timestamp: float) -> None:
        if isinstance(content, MCPServerToolCallContent):
            state = self._ensure_tool_state(content.call_id)
            state.record_start()
            state.name = content.tool_name or state.name
            state.server_name = content.server_name or state.server_name
            state.argument_fragments.append(_safe_serialize(content.arguments))
        elif isinstance(content, MCPServerToolResultContent):
            state = self._ensure_tool_state(content.call_id)
            if state.started_perf is None:
                state.started_perf = perf_timestamp
                state.started_at = _utc_now()
            state.output_fragments.append(_safe_serialize(content.output))
            # Screenshot payload estimation
            tool_name_l = (state.name or "").lower()
            if tool_name_l == "take_screenshot" or ("screenshot" in tool_name_l):
                self.screenshot_calls_count += 1
                # Prefer base64 if present; otherwise estimate from file size
                b64_len = _extract_base64_length(content.output)
                if b64_len > 0:
                    self.screenshot_base64_chars_total += b64_len
                else:
                    self.screenshot_bytes_total += _estimate_bytes_from_pathlike(content.output)
            state.record_completion()
        elif isinstance(content, FunctionCallContent):
            state = self._ensure_tool_state(content.call_id)
            state.record_start()
            state.name = content.name or state.name
            state.argument_fragments.append(_safe_serialize(content.arguments))
        elif isinstance(content, FunctionResultContent):
            state = self._ensure_tool_state(content.call_id)
            if state.started_perf is None:
                state.started_perf = perf_timestamp
                state.started_at = _utc_now()
            state.output_fragments.append(_safe_serialize(content.result))
            if getattr(content, "exception", None) is not None:
                state.error = True
            state.record_completion()

    def finalize(self) -> tuple[Dict[str, Any], Optional[UsageDetails]]:
        completed_at = _utc_now()
        duration = max(time.perf_counter() - self.started_perf, 0.0)
        aggregated = AgentResponse.from_agent_run_response_updates(self.updates) if self.updates else None
        usage_obj: Optional[UsageDetails] = getattr(aggregated, "usage_details", None) if aggregated else None
        usage = _usage_to_dict(usage_obj)
        response_meta = {
            "response_id": getattr(aggregated, "response_id", None) if aggregated else None,
            "created_at": _safe_serialize(getattr(aggregated, "created_at", None)) if aggregated else None,
            "additional_properties": _safe_serialize(getattr(aggregated, "additional_properties", None))
            if aggregated
            else None,
            "message_count": len(getattr(aggregated, "messages", [])) if aggregated else 0,
            "text_excerpt": _safe_serialize(aggregated.text) if aggregated else None,
        }
        tool_records = [state.to_dict() for state in self.tool_calls.values()] if self.tool_calls else []
        # Estimate tokens contributed by screenshots
        # If we had base64 chars, estimate tokens ~ chars/4. If only bytes, estimate base64 chars as bytes*4/3.
        estimated_tokens_from_screenshots = 0
        try:
            base64_chars = self.screenshot_base64_chars_total
            bytes_total = self.screenshot_bytes_total
            if base64_chars > 0:
                estimated_tokens_from_screenshots = int(base64_chars / 4)
            elif bytes_total > 0:
                estimated_tokens_from_screenshots = int(((bytes_total * 4) / 3) / 4)
        except Exception:
            estimated_tokens_from_screenshots = 0

        record = {
            "suite_name": self.suite_name,
            "suite_index": self.suite_index,
            "suite_total": self.suite_total,
            "started_at": _to_iso(self.started_at),
            "completed_at": _to_iso(completed_at),
            "duration_seconds": duration,
            "updates_count": len(self.updates),
            "total_text_chars": self.total_text_chars,
            "usage": usage,
            "screenshots": {
                "calls": self.screenshot_calls_count,
                "base64_chars_total": self.screenshot_base64_chars_total or None,
                "bytes_total": self.screenshot_bytes_total or None,
                "estimated_input_tokens": estimated_tokens_from_screenshots or None,
            },
            "response": response_meta,
            "tool_calls": tool_records,
            "stream_events": self.stream_events,
        }
        return record, usage_obj


class AgentRunMetricsCollector:
    """Collects per-suite and aggregate metrics for agent streaming runs."""

    def __init__(self, *, plan_path: str, base_url: Optional[str], suite_total: int) -> None:
        self.plan_path = plan_path
        self.base_url = base_url
        self.suite_total = suite_total
        self.run_started_at = _utc_now()
        self.run_started_perf = time.perf_counter()
        self._active_suite: Optional[SuiteMetricRecord] = None
        self._completed_suites: List[Dict[str, Any]] = []
        self._aggregate_usage: Optional[UsageDetails] = None

    def start_suite(self, suite_name: Optional[str], suite_index: int) -> None:
        if self._active_suite is not None:
            raise RuntimeError("A suite is already active; finalize it before starting a new one.")
        self._active_suite = SuiteMetricRecord(
            suite_name=suite_name,
            suite_index=suite_index,
            suite_total=self.suite_total,
            started_at=_utc_now(),
            started_perf=time.perf_counter(),
        )

    def record_update(self, update: AgentResponseUpdate) -> None:
        if self._active_suite is None:
            return
        received_at = _utc_now()
        perf_ts = time.perf_counter()
        self._active_suite.append_update(update, received_at=received_at, perf_timestamp=perf_ts)

    def finish_suite(self) -> Dict[str, Any]:
        if self._active_suite is None:
            raise RuntimeError("No active suite to finalize.")
        record, usage_obj = self._active_suite.finalize()
        if usage_obj:
            if self._aggregate_usage is None:
                self._aggregate_usage = usage_obj
            else:
                self._aggregate_usage += usage_obj
        self._completed_suites.append(record)
        self._active_suite = None
        return record

    def abort_active_suite(self) -> Optional[Dict[str, Any]]:
        if self._active_suite is None:
            return None
        record, usage_obj = self._active_suite.finalize()
        if usage_obj:
            if self._aggregate_usage is None:
                self._aggregate_usage = usage_obj
            else:
                self._aggregate_usage += usage_obj
        record["aborted"] = True
        self._completed_suites.append(record)
        self._active_suite = None
        return record

    def finalize_run(self) -> Dict[str, Any]:
        if self._active_suite is not None:
            raise RuntimeError("Cannot finalize run while a suite is still active.")
        completed_at = _utc_now()
        duration = max(time.perf_counter() - self.run_started_perf, 0.0)
        # Aggregate screenshot estimates across suites
        screenshot_calls = 0
        screenshot_tokens = 0
        for s in self._completed_suites:
            sc = s.get("screenshots", {}) or {}
            screenshot_calls += int(sc.get("calls", 0) or 0)
            screenshot_tokens += int(sc.get("estimated_input_tokens", 0) or 0)
        return {
            "run": {
                "plan_path": self.plan_path,
                "base_url": self.base_url,
                "suite_total": self.suite_total,
                "started_at": _to_iso(self.run_started_at),
                "completed_at": _to_iso(completed_at),
                "duration_seconds": duration,
                "usage": _usage_to_dict(self._aggregate_usage),
                "screenshots": {
                    "calls": screenshot_calls or None,
                    "estimated_input_tokens": screenshot_tokens or None,
                },
            },
            "suites": self._completed_suites,
        }

    @property
    def completed_suites(self) -> Iterable[Dict[str, Any]]:
        return list(self._completed_suites)


def _sanitize_structure(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize_structure(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_structure(item) for item in value]
    return _safe_serialize(value)


def dump_metrics_to_file(metrics: Dict[str, Any], target_path: Path) -> None:
    sanitized = _sanitize_structure(metrics)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")
