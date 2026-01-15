from __future__ import annotations

import json
import logging
import os
from typing import Any, Iterable, Sequence

# Optional: agent_framework rich types may not be present in all installs.
# Avoid importing them so this utility remains functional with lean environments.

_DEBUG_ENV_VALUES = {"1", "true", "yes", "on"}


def _debug_metadata_enabled() -> bool:
    value = os.getenv("AGENT_FRAMEWORK_DEBUG_METADATA", "")
    return value.strip().lower() in _DEBUG_ENV_VALUES


def _stringify(value: Any) -> Any:
    """Best-effort conversion of complex objects into JSON-friendly data."""
    if value is None:
        return None
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return value.to_dict(exclude=None, exclude_none=True)
        except TypeError:
            return value.to_dict()
        except Exception:
            return repr(value)
    if hasattr(value, "value"):
        candidate = getattr(value, "value")
        if candidate is not None:
            return candidate
    if isinstance(value, (list, tuple, set)):
        return [_stringify(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _stringify(val) for key, val in value.items() if val is not None}
    return value


def log_agent_response_metadata(
    agent_label: str,
    response: Any,
    *,
    logger: logging.Logger,
    include_message_count: bool = False,
    force: bool = False,
) -> None:
    """Log metadata for a non-streaming agent response if diagnostics are enabled."""
    if not (force or _debug_metadata_enabled()):
        return

    if response is None:
        logger.info("[%s] Agent response is None; no metadata available.", agent_label)
        return

    metadata: dict[str, Any] = {}

    for attr in ("response_id", "conversation_id", "model_id", "created_at", "finish_reason"):
        if hasattr(response, attr):
            value = getattr(response, attr)
            if value is not None:
                metadata[attr] = _stringify(value)

    usage = getattr(response, "usage_details", None)
    if usage is not None:
        usage_dict = _stringify(usage)
        if usage_dict:
            metadata["usage"] = usage_dict

    additional = getattr(response, "additional_properties", None)
    if additional:
        metadata["additional_properties"] = _stringify(additional)

    if include_message_count and hasattr(response, "messages"):
        messages = getattr(response, "messages")
        try:
            metadata["message_count"] = len(messages)
        except Exception:
            metadata["message_count"] = "unknown"

    if not metadata and hasattr(response, "to_dict") and callable(response.to_dict):
        try:
            metadata = response.to_dict(exclude={"messages", "contents"}, exclude_none=True)
        except Exception:
            metadata = {"repr": repr(response)}

    logger.info("[%s] Agent response metadata: %s", agent_label, json.dumps(metadata, default=str))


def log_agent_stream_metadata(
    agent_label: str,
    updates: Sequence[Any] | Iterable[Any] | None,
    *,
    logger: logging.Logger,
    force: bool = False,
) -> None:
    """Best-effort summary of streaming updates without requiring agent_framework types."""
    if not (force or _debug_metadata_enabled()):
        return

    if not updates:
        logger.info("[%s] No streaming updates captured; skipping metadata log.", agent_label)
        return

    total = 0
    text_len = 0
    last_finish_reason = None
    tool_calls = 0
    for upd in updates:
        total += 1
        txt = getattr(upd, "text", None)
        if isinstance(txt, str):
            text_len += len(txt)
        fr = getattr(upd, "finish_reason", None)
        if fr:
            last_finish_reason = fr
        # Heuristic: some update types may carry a 'tool_name' or 'tool_call' attribute
        if getattr(upd, "tool_name", None) or getattr(upd, "tool_call", None):
            tool_calls += 1

    summary = {
        "updates_count": total,
        "total_text_chars": text_len,
        "last_finish_reason": _stringify(last_finish_reason),
        "tool_calls_detected": tool_calls,
    }
    logger.info("[%s] Stream summary: %s", agent_label, json.dumps(summary, default=str))