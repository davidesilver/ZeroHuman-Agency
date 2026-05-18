"""LLM provider abstraction layer.

Provides:
  - LLMProvider: abstract interface all providers implement
  - Registrar: dict of provider_name → LLMProvider
  - record_call: telemetry sink for llm_provider_metrics table
  - call_with_telemetry: thin wrapper over call_llm with telemetry emission

The existing call_llm() in utils/llm_client.py remains the primary entry point.
This layer wraps it and emits a row to llm_provider_metrics on each call.
"""

from .provider import LLMProvider, LLMRequest, LLMResult
from .registrar import get_registrar, list_providers, register_provider
from .telemetry import call_with_telemetry, record_llm_call

__all__ = [
    "LLMProvider",
    "LLMRequest",
    "LLMResult",
    "get_registrar",
    "register_provider",
    "list_providers",
    "record_llm_call",
    "call_with_telemetry",
]
