"""Local CLI upstream adapter.

Routes inference through a locally installed and authenticated CLI tool
(claude, gemini, etc.) instead of a remote API. The adapter spawns the
CLI as a subprocess and translates the response to OpenAI-compatible JSON,
which the proxy server then forwards back to the cadoo agent loop.

Supported CLIs (auto-detected in preference order):
  - claude   (Claude Code, ``claude -p --output-format json``)
  - gemini   (Gemini CLI,  ``gemini -p``)

No API keys or tokens are needed — authentication is handled by the CLI itself.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from typing import FrozenSet, List, Optional

from cadoo_cli.proxy.adapters.base import UpstreamAdapter, UpstreamCredential

logger = logging.getLogger(__name__)

# Sentinel base URL used internally — the proxy uses this to identify the
# local-cli path and bypasses normal HTTP forwarding.
LOCAL_CLI_BASE_URL = "http://local-cli.internal/v1"

_ALLOWED_PATHS: FrozenSet[str] = frozenset(
    {"/chat/completions", "/completions", "/models"}
)

# CLI preference order: first found wins.
_CLI_PREFERENCE = ["claude", "gemini"]


def detect_available_cli() -> Optional[str]:
    """Return the first available CLI executable name, or None."""
    preferred = os.environ.get("CADOO_LOCAL_CLI", "").strip()
    if preferred and shutil.which(preferred):
        return preferred
    for name in _CLI_PREFERENCE:
        if shutil.which(name):
            return name
    return None


def call_local_cli(
    cli: str,
    messages: List[dict],
    model: Optional[str] = None,
    *,
    stream: bool = False,
) -> dict:
    """Call the local CLI and return an OpenAI-compatible response dict.

    Args:
        cli:      CLI executable name (``"claude"`` or ``"gemini"``).
        messages: OpenAI-format message list.
        model:    Model hint forwarded to the CLI when supported.
        stream:   Reserved — local CLI doesn't stream; always False.
    """
    # Build the prompt from the messages list.
    # System messages are prepended; the last user message is the main prompt.
    system_parts: List[str] = []
    user_parts: List[str] = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )
        content = str(content).strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        elif role in ("user", "assistant"):
            label = "User" if role == "user" else "Assistant"
            user_parts.append(f"{label}: {content}")

    prompt = "\n\n".join(user_parts).strip() or "Hello"

    t0 = time.time()

    if cli == "claude":
        cmd = ["claude", "-p", "--output-format", "json"]
        # Only pass --model when it looks like a full versioned ID (contains a date
        # or the "us." prefix). Short names like "claude-sonnet-4-6" are rejected
        # by the claude CLI — it uses its own configured model by default.
        if model and (model.startswith("us.") or any(c.isdigit() and len(model) > 20 for c in model)):
            cmd += ["--model", model]
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,
        )
        elapsed = time.time() - t0
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"claude CLI exited with code {result.returncode}: {stderr}"
            )
        try:
            data = json.loads(result.stdout)
            text = data.get("result", result.stdout.strip())
        except (json.JSONDecodeError, AttributeError):
            text = result.stdout.strip()

    elif cli == "gemini":
        cmd = ["gemini", "-p", prompt]
        if model:
            cmd += ["--model", model]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        elapsed = time.time() - t0
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"gemini CLI exited with code {result.returncode}: {stderr}"
            )
        text = result.stdout.strip()

    else:
        # Generic: pass prompt via stdin, capture stdout
        result = subprocess.run(
            [cli, prompt],
            capture_output=True,
            text=True,
            timeout=300,
        )
        elapsed = time.time() - t0
        if result.returncode != 0:
            raise RuntimeError(
                f"{cli} exited with code {result.returncode}: {result.stderr.strip()}"
            )
        text = result.stdout.strip()

    # Return OpenAI-compatible response
    used_model = model or cli
    return {
        "id": f"localcli-{int(t0)}",
        "object": "chat.completion",
        "created": int(t0),
        "model": used_model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "_local_cli": cli,
        "_elapsed_ms": int(elapsed * 1000),
    }


class LocalCliAdapter(UpstreamAdapter):
    """Proxy upstream that delegates to a locally installed CLI (claude/gemini)."""

    def __init__(self, cli: Optional[str] = None) -> None:
        self._cli = cli or detect_available_cli()

    @property
    def name(self) -> str:
        return "local-cli"

    @property
    def display_name(self) -> str:
        cli = self._cli or "none"
        return f"Local CLI ({cli})"

    @property
    def allowed_paths(self) -> FrozenSet[str]:
        return _ALLOWED_PATHS

    def is_authenticated(self) -> bool:
        return bool(self._cli and shutil.which(self._cli))

    def get_credential(self) -> UpstreamCredential:
        if not self._cli:
            raise RuntimeError(
                "No local CLI found. Install claude (Claude Code) or gemini (Gemini CLI)."
            )
        if not shutil.which(self._cli):
            raise RuntimeError(
                f"CLI '{self._cli}' not found in PATH. "
                "Install it and make sure it is authenticated."
            )
        return UpstreamCredential(
            bearer="local-cli",
            base_url=LOCAL_CLI_BASE_URL,
        )


__all__ = ["LocalCliAdapter", "detect_available_cli", "call_local_cli", "LOCAL_CLI_BASE_URL"]
