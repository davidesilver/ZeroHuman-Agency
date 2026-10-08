import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_engine.config import settings
from content_engine.services.llm import codex_subscription as codex
from content_engine.services.llm.provider import LLMRequest


def output(*events):
    return "\n".join(json.dumps(event) for event in events).encode()


SUCCESS = output(
    {"type": "item.completed", "item": {"type": "agent_message", "text": '{"title":"Test"}'}},
    {"type": "turn.completed", "usage": {"input_tokens": 12, "output_tokens": 8}},
)


def test_result_preserves_usage_and_unknown_bill():
    result = codex._result(SUCCESS, 0, time.monotonic())
    assert result.content == '{"title":"Test"}'
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 8
    assert result.cost_usd is None
    assert result.provider == "codex_subscription"


@pytest.mark.parametrize("stdout,code", [
    (SUCCESS, 1), (b"not json", 0), (b"", 0),
    (output({"type": "turn.failed"}), 0),
    (output({"type": "item.completed", "item": {"type": "command_execution"}}), 0),
    (output({"type": "item.completed", "item": {"type": "agent_message", "text": "partial"}}), 0),
])
def test_failures_are_closed(stdout, code):
    with pytest.raises(RuntimeError):
        codex._result(stdout, code, time.monotonic())


def test_environment_and_command(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-value")
    monkeypatch.setenv("OPENROUTER_API_KEY", "private-test-value")
    assert "OPENAI_API_KEY" not in codex._environment()
    assert "OPENROUTER_API_KEY" not in codex._environment()
    with patch.object(codex.shutil, "which", return_value="/bin/codex"):
        cmd = codex._command("/tmp/work")
    assert '--ignore-user-config' in cmd
    assert 'forced_login_method="chatgpt"' in cmd
    assert "shell_tool" in cmd
    assert cmd[-1] == "-"


def test_missing_binary():
    with patch.object(codex.shutil, "which", return_value=None), pytest.raises(RuntimeError):
        codex._command("/tmp/work")


async def test_sync_provider_works_in_running_async_application(monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "codex_subscription")
    proc = MagicMock(stdout=SUCCESS, returncode=0)
    with patch.object(codex.subprocess, "run", return_value=proc), \
         patch.object(codex.shutil, "which", return_value="/bin/codex"):
        result = codex.CodexSubscriptionProvider().complete(LLMRequest(prompt="test"))
    assert result.provider == "codex_subscription"


def test_unrecognized_config_diagnostic_is_rejected():
    bad = output({"type": "item.completed", "item": {"type": "error", "message": "ignored config"}})
    with pytest.raises(RuntimeError):
        codex._result(bad + b"\n" + SUCCESS, 0, time.monotonic())


def test_known_disabled_host_diagnostic_is_allowed():
    diagnostic = output({"type": "item.completed", "item": {
        "type": "error", "message": "Code Mode is unavailable because code-mode host is disabled.",
    }})
    assert codex._result(diagnostic + b"\n" + SUCCESS, 0, time.monotonic()).content


async def test_async_inference_sends_prompt_on_stdin():
    proc = MagicMock(returncode=0)
    proc.communicate = AsyncMock(return_value=(SUCCESS, b""))
    with patch.object(codex.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)), \
         patch.object(codex.shutil, "which", return_value="/bin/codex"):
        result = await codex.complete_async(LLMRequest(prompt="fictional", system_prompt="Italian"))
    assert result.provider == "codex_subscription"
    assert b"Italian" in proc.communicate.call_args.args[0]


@pytest.mark.parametrize("failure", [TimeoutError, asyncio.CancelledError])
async def test_timeout_and_cancellation_reap_process(failure):
    proc = MagicMock(returncode=None)
    proc.communicate = AsyncMock(side_effect=[failure(), (b"", b"")])
    with patch.object(codex.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)), \
         patch.object(codex.shutil, "which", return_value="/bin/codex"), pytest.raises(failure):
        await codex.complete_async(LLMRequest(prompt="test"))
    proc.kill.assert_called_once()
    assert proc.communicate.await_count == 2


async def test_main_routing_never_uses_api_fallback(monkeypatch):
    from content_engine.utils import llm_client
    monkeypatch.setattr(settings, "llm_mode", "codex_subscription")
    with patch.object(codex, "complete_async", AsyncMock(side_effect=RuntimeError("quota"))), \
         patch.object(llm_client, "_call_llm_parallel", AsyncMock()) as api, \
         pytest.raises(RuntimeError, match="quota"):
        await llm_client.call_llm("test", "brand")
    api.assert_not_called()


async def test_main_routing_preserves_content_and_heartbeat(monkeypatch):
    from content_engine.utils import llm_client
    monkeypatch.setattr(settings, "llm_mode", "codex_subscription")
    result = codex._result(SUCCESS, 0, time.monotonic())
    heartbeat = AsyncMock()
    with patch.object(codex, "complete_async", AsyncMock(return_value=result)), \
         patch.object(llm_client, "_record_heartbeat_safely", heartbeat):
        response = await llm_client.call_llm("test", "brand", system_prompt="Italian")
        await asyncio.sleep(0)
    assert response.content == result.content
    assert response.engine == "codex_subscription"
    assert response.cost_usd is None
    heartbeat.assert_awaited_once()


def test_registrar_ignores_byok_in_subscription_mode(monkeypatch):
    from content_engine.services.llm.registrar import get_registrar
    monkeypatch.setattr(settings, "llm_mode", "codex_subscription")
    assert get_registrar().get_for_brand("brand", preferred="anthropic").name == "codex_subscription"


async def test_humanizer_model_override_uses_subscription(monkeypatch):
    from content_engine.agents import humanizer
    monkeypatch.setattr(settings, "llm_mode", "codex_subscription")
    with patch.object(humanizer, "call_llm", AsyncMock(return_value="ok")) as call:
        result = await humanizer._call_llm_with_model("test", "brand", "api-model", "editing", "rewrite")
    assert result == "ok"
    assert call.call_args.kwargs["task_type"] == "editing"
