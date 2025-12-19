from __future__ import annotations

import subprocess
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from agent_framework import ai_function

_EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".md": "markdown",
}

def _resolve_path(raw_path: Optional[str]) -> Path:
    if not raw_path:
        return Path.cwd() / "artifacts"
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return Path.cwd() / candidate

def _describe_children(folder: Path, limit: int = 50) -> List[Dict[str, object]]:
    children: List[Dict[str, object]] = []
    for entry in folder.iterdir():
        kind = "directory" if entry.is_dir() else "file"
        children.append({
            "name": entry.name,
            "type": kind,
            "size_bytes": entry.stat().st_size if entry.is_file() else None,
        })
        if len(children) >= limit:
            break
    return children


def _detect_language(path: Path) -> Optional[str]:
    return _EXTENSION_LANGUAGE_MAP.get(path.suffix.lower())


@ai_function(
    name="get_file_info",
    description="Inspect a path for source files or directories and describe its structure, size, and detected language (if applicable).",
)
def get_file_info(path: Optional[str] = None) -> Dict[str, object]:
    target = _resolve_path(path)
    exists = target.exists()
    info: Dict[str, object] = {
        "path": str(target),
        "exists": exists,
        "is_file": target.is_file() if exists else False,
        "is_dir": target.is_dir() if exists else False,
    }
    if not exists:
        return info
    if target.is_file():
        info["size_bytes"] = target.stat().st_size
        language = _detect_language(target)
        if language:
            info["language"] = language
    else:
        info["children"] = _describe_children(target)
    return info


@ai_function(
    name="get_file_contents",
    description="Read a UTF-8 source file (HTML, CSS, JS, Python, etc.) and return its contents for analysis before editing.",
)
def get_file_contents(path: str, max_bytes: int = 8192) -> Dict[str, object]:
    target = _resolve_path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {target}")
    if not target.is_file():
        raise IsADirectoryError(f"Expected a file but found a directory: {target}")
    raw_text = target.read_text(encoding="utf-8", errors="replace")
    raw_bytes = raw_text.encode("utf-8")
    truncated = len(raw_bytes) > max_bytes
    if truncated:
        raw_bytes = raw_bytes[:max_bytes]
        raw_text = raw_bytes.decode("utf-8", errors="ignore")
    language = _detect_language(target)
    return {
        "path": str(target),
        "truncated": truncated,
        "content": raw_text,
        "language": language,
    }


@ai_function(
    name="write_file",
    description="Create or overwrite a UTF-8 source file (HTML, CSS, JS, Python, etc.) at the given path.",
)
def write_file(
    path: str,
    content: str,
    create_dirs: bool = True,
    ensure_trailing_newline: bool = True,
) -> Dict[str, object]:
    target = _resolve_path(path)
    if create_dirs:
        target.parent.mkdir(parents=True, exist_ok=True)
    if ensure_trailing_newline and content and not content.endswith("\n"):
        content = content + "\n"
    target.write_text(content, encoding="utf-8")
    language = _detect_language(target)
    return {
        "path": str(target),
        "bytes_written": len(content.encode("utf-8")),
        "language": language,
    }


@ai_function(
    name="run_python_file",
    description="Run a Python file and return its exit code along with captured stdout and stderr.",
)
def run_python_file(path: str, timeout_seconds: int = 60) -> Dict[str, object]:
    target = _resolve_path(path)
    if not target.exists():
        raise FileNotFoundError(f"Python file not found: {target}")
    if not target.is_file():
        raise IsADirectoryError(f"Expected a file but found a directory: {target}")
    command = [sys.executable, str(target)]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=target.parent,
        )
        return {
            "path": str(target),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "path": str(target),
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout": True,
        }
