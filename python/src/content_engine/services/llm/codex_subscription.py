"""Owner-operated text inference through the official ChatGPT-authenticated CLI.

No token extraction, API fallback, personal config, or model-generated shell tools.
The backend must run as the same OS user who completed `codex login`.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import time

from ...config import settings
from .provider import LLMProvider, LLMRequest, LLMResult


def _environment() -> dict[str, str]:
    # Do not pass backend API keys, brand secrets, or arbitrary process variables.
    allowed = ("HOME", "PATH", "CODEX_HOME", "TMPDIR", "LANG", "LC_ALL", "SSL_CERT_FILE")
    return {key: os.environ[key] for key in allowed if key in os.environ}


def _command(workdir: str) -> list[str]:
    binary = shutil.which("codex")
    if not binary:
        raise RuntimeError("Codex CLI missing; install the official CLI and run codex login")
    command = [
        binary, "exec", "--strict-config", "--ignore-user-config", "--ignore-rules", "--ephemeral",
        "--skip-git-repo-check", "--sandbox", "read-only", "--json", "--color", "never",
        "--cd", workdir,
        "-c", 'forced_login_method="chatgpt"',
        "-c", 'approval_policy="never"',
        "-c", 'web_search="disabled"',
        "-c", "project_doc_max_bytes=0",
    ]
    for feature in (
        "shell_tool", "unified_exec", "apps", "hooks", "plugins", "multi_agent",
        "browser_use", "browser_use_external", "browser_use_full_cdp_access",
        "computer_use", "in_app_browser", "code_mode", "code_mode_host",
        "view_image", "image_generation",
    ):
        command.extend(["--disable", feature])
    if settings.codex_model:
        command.extend(["--model", settings.codex_model])
    command.append("-")
    return command


def _prompt(request: LLMRequest) -> bytes:
    return (
        "Produce only the requested text. Do not use tools or inspect files.\n\n"
        + (f"Instructions:\n{request.system_prompt}\n\n" if request.system_prompt else "")
        + f"Request:\n{request.prompt}"
    ).encode()


def _result(stdout: bytes, returncode: int, started: float) -> LLMResult:
    # Never echo stderr: it can contain prompt data or account information.
    if returncode:
        raise RuntimeError(f"Codex subscription failed (exit {returncode}); check login/quota")
    messages: list[str] = []
    usage = None
    for line in stdout.decode().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Invalid Codex JSONL response") from exc
        kind = event.get("type")
        if kind in ("error", "turn.failed"):
            raise RuntimeError("Codex subscription turn failed; no API fallback attempted")
        if kind == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                messages.append(item.get("text", ""))
            elif item.get("type") == "error" and item.get("message", "").startswith(
                "Code Mode is unavailable because code-mode host is disabled."
            ):
                # The installed CLI emits this diagnostic when its host is disabled.
                pass
            elif item.get("type") not in ("reasoning", "todo_list"):
                raise RuntimeError("Unexpected Codex tool activity in text-only inference")
        if kind == "turn.completed":
            usage = event.get("usage")
    if not messages or not isinstance(usage, dict):
        raise RuntimeError("Codex did not complete a text inference turn with usage")
    return LLMResult(
        content="\n".join(messages), model_used=settings.codex_model or "codex-default",
        provider="codex_subscription", prompt_tokens=usage["input_tokens"],
        completion_tokens=usage["output_tokens"],
        latency_ms=int((time.monotonic() - started) * 1000), cost_usd=None,
    )


async def complete_async(request: LLMRequest) -> LLMResult:
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="zerohuman-codex-") as workdir:
        proc = await asyncio.create_subprocess_exec(
            *_command(workdir), stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env=_environment(), cwd=workdir,
        )
        try:
            stdout, _ = await asyncio.wait_for(
                proc.communicate(_prompt(request)), settings.codex_timeout_seconds,
            )
        except (TimeoutError, asyncio.CancelledError):
            if proc.returncode is None:
                proc.kill()
            await proc.communicate()
            raise
        return _result(stdout, proc.returncode, started)


class CodexSubscriptionProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "codex_subscription"

    def is_available(self, brand_id: str) -> bool:
        # Actual login/quota eligibility is verified by a successful inference turn.
        return settings.llm_mode == "codex_subscription" and shutil.which("codex") is not None

    def complete(self, request: LLMRequest) -> LLMResult:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="zerohuman-codex-") as workdir:
            proc = subprocess.run(
                _command(workdir), input=_prompt(request), capture_output=True,
                timeout=settings.codex_timeout_seconds, env=_environment(), cwd=workdir,
                check=False,
            )
            return _result(proc.stdout, proc.returncode, started)
