"""Generic async runner for PrintingPress CLI binaries.

Usage:
    from .cli_runner import run_cli, CLINotFoundError

    try:
        data = await run_cli("x-twitter", ["search", query, "--max-results", "50"],
                             env_extra={"X_BEARER_TOKEN": token})
    except CLINotFoundError:
        # binary not installed — caller falls back to httpx
        ...
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from typing import Any

logger = logging.getLogger(__name__)

_TIMEOUT_DEFAULT = 30.0
# Common non-PATH install locations for Go/npm binaries
_EXTRA_BIN_DIRS = (
    os.path.expanduser("~/.local/bin"),
    os.path.expanduser("~/go/bin"),
    "/usr/local/bin",
    "/opt/homebrew/bin",
)


class CLINotFoundError(RuntimeError):
    """Raised when a CLI binary is not found in PATH or common install dirs."""


def _find_binary(name: str) -> str | None:
    path = shutil.which(name)
    if path:
        return path
    for d in _EXTRA_BIN_DIRS:
        candidate = os.path.join(d, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


async def run_cli_for_brand(
    binary: str,
    args: list[str],
    *,
    brand_id: str,
    service_name: str,
    env_extra: dict[str, str] | None = None,
    timeout: float = _TIMEOUT_DEFAULT,
) -> Any:
    """Like run_cli, but injects brand-specific credentials from the vault.

    Vault credentials take priority over env_extra, which takes priority
    over the process environment. Falls back gracefully if vault is not
    configured (credentials come from global env / env_extra only).
    """
    from ..services.credential_vault import get_env_for_brand
    brand_env = await get_env_for_brand(brand_id, service_name)
    merged = {**(env_extra or {}), **brand_env}
    return await run_cli(binary, args, env_extra=merged, timeout=timeout)


async def run_cli(
    binary: str,
    args: list[str],
    *,
    env_extra: dict[str, str] | None = None,
    timeout: float = _TIMEOUT_DEFAULT,
) -> Any:
    """Execute a PrintingPress CLI binary and return parsed JSON stdout.

    Args:
        binary:    Binary name (e.g. "x-twitter", "firecrawl").
        args:      Positional args and flags passed to the binary.
        env_extra: Additional env vars injected for this call only.
                   Use this to pass API keys — never put them in args.
        timeout:   Max seconds to wait for the subprocess.

    Returns:
        Parsed JSON value (list or dict). Empty list if stdout is empty.

    Raises:
        CLINotFoundError: Binary not in PATH or common install dirs.
        RuntimeError:     Non-zero exit, timeout, or invalid JSON output.
    """
    path = _find_binary(binary)
    if path is None:
        raise CLINotFoundError(f"CLI binary '{binary}' not found in PATH or common install dirs")

    env = {**os.environ}
    if env_extra:
        env.update(env_extra)

    try:
        proc = await asyncio.create_subprocess_exec(
            path,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to launch '{binary}': {exc}") from exc

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise RuntimeError(f"CLI '{binary}' timed out after {timeout}s")

    if proc.returncode != 0:
        err = stderr.decode(errors="replace").strip()[:500]
        raise RuntimeError(f"CLI '{binary}' exited {proc.returncode}: {err}")

    raw = stdout.decode(errors="replace").strip()
    if not raw:
        return []

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        preview = raw[:200]
        raise RuntimeError(f"CLI '{binary}' output is not valid JSON: {exc} — got: {preview!r}") from exc
