"""Static catalog of all supported LLM providers.

Each ProviderDefinition describes metadata only — no credentials, no live state.
Use GenericOpenAIProvider or AnthropicDirectProvider to make actual calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderDefinition:
    id: str
    display_name: str
    category: str          # "direct" | "gateway" | "meta_router"
    api_type: str          # "openai_compatible" | "anthropic_native"
    auth_type: str         # "api_key" | "none" | "optional_key"
    default_base_url: str
    base_url_editable: bool
    billing_model: str     # "pay_per_use" | "subscription" | "free" | "self_hosted" | "prepaid"
    key_prefix: str        # validates key format (empty = no prefix check)
    key_validation: str    # "models_list" | "chat_completion" | "none"
    models: tuple[str, ...] = field(default_factory=tuple)  # empty = discovered at runtime
    priority: int = 0      # 0=P0, 1=P1, 2=P2
    docs_url: str = ""
    logo: str = ""         # provider slug used for logo lookup in UI


# ---------------------------------------------------------------------------
# Direct providers — P0 (must have at least one of these for a working system)
# ---------------------------------------------------------------------------

_ANTHROPIC = ProviderDefinition(
    id="anthropic",
    display_name="Anthropic",
    category="direct",
    api_type="anthropic_native",
    auth_type="api_key",
    default_base_url="https://api.anthropic.com",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="sk-ant-",
    key_validation="chat_completion",
    models=(
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-haiku-4-20250514",
    ),
    priority=0,
    docs_url="https://console.anthropic.com/settings/keys",
    logo="anthropic",
)

_OPENAI = ProviderDefinition(
    id="openai",
    display_name="OpenAI",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://api.openai.com/v1",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="sk-",
    key_validation="models_list",
    models=("gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o3-mini"),
    priority=0,
    docs_url="https://platform.openai.com/api-keys",
    logo="openai",
)

_GOOGLE = ProviderDefinition(
    id="google",
    display_name="Google AI (Gemini)",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="",
    key_validation="models_list",
    models=("gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"),
    priority=0,
    docs_url="https://aistudio.google.com/apikey",
    logo="google",
)

_GROQ = ProviderDefinition(
    id="groq",
    display_name="Groq",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://api.groq.com/openai/v1",
    base_url_editable=False,
    billing_model="free",
    key_prefix="gsk_",
    key_validation="models_list",
    models=(
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
        "mixtral-8x7b-32768",
    ),
    priority=0,
    docs_url="https://console.groq.com/keys",
    logo="groq",
)

# ---------------------------------------------------------------------------
# Direct providers — P1
# ---------------------------------------------------------------------------

_DEEPSEEK = ProviderDefinition(
    id="deepseek",
    display_name="DeepSeek",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://api.deepseek.com/v1",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="sk-",
    key_validation="models_list",
    models=("deepseek-chat", "deepseek-reasoner"),
    priority=1,
    docs_url="https://platform.deepseek.com/api_keys",
    logo="deepseek",
)

_MISTRAL = ProviderDefinition(
    id="mistral",
    display_name="Mistral AI",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://api.mistral.ai/v1",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="",
    key_validation="models_list",
    models=("mistral-large-latest", "mistral-small-latest", "codestral-latest"),
    priority=1,
    docs_url="https://console.mistral.ai/api-keys",
    logo="mistral",
)

_XAI = ProviderDefinition(
    id="xai",
    display_name="xAI (Grok)",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://api.x.ai/v1",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="xai-",
    key_validation="models_list",
    models=("grok-3", "grok-3-mini", "grok-2-1212"),
    priority=1,
    docs_url="https://console.x.ai",
    logo="xai",
)

_TOGETHER = ProviderDefinition(
    id="together",
    display_name="Together AI",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://api.together.xyz/v1",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="",
    key_validation="models_list",
    models=(
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "Qwen/Qwen2.5-72B-Instruct-Turbo",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
    ),
    priority=1,
    docs_url="https://api.together.ai/settings/api-keys",
    logo="together",
)

# ---------------------------------------------------------------------------
# Direct providers — P2
# ---------------------------------------------------------------------------

_FIREWORKS = ProviderDefinition(
    id="fireworks",
    display_name="Fireworks AI",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://api.fireworks.ai/inference/v1",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="fw_",
    key_validation="models_list",
    models=("accounts/fireworks/models/llama-v3p3-70b-instruct",),
    priority=2,
    docs_url="https://fireworks.ai/account/api-keys",
    logo="fireworks",
)

_NVIDIA = ProviderDefinition(
    id="nvidia",
    display_name="NVIDIA NIM",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://integrate.api.nvidia.com/v1",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="nvapi-",
    key_validation="models_list",
    models=("meta/llama-3.1-70b-instruct", "nvidia/llama-3.1-nemotron-70b-instruct"),
    priority=2,
    docs_url="https://build.nvidia.com/nim",
    logo="nvidia",
)

_PERPLEXITY = ProviderDefinition(
    id="perplexity",
    display_name="Perplexity",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://api.perplexity.ai",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="pplx-",
    key_validation="chat_completion",
    models=("sonar", "sonar-pro", "sonar-reasoning", "sonar-reasoning-pro"),
    priority=2,
    docs_url="https://www.perplexity.ai/settings/api",
    logo="perplexity",
)

_MOONSHOT = ProviderDefinition(
    id="moonshot",
    display_name="Moonshot AI (Kimi)",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://api.moonshot.ai/v1",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="sk-",
    key_validation="models_list",
    models=("moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"),
    priority=2,
    docs_url="https://platform.moonshot.ai/console/api-keys",
    logo="moonshot",
)

_CEREBRAS = ProviderDefinition(
    id="cerebras",
    display_name="Cerebras",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://api.cerebras.ai/v1",
    base_url_editable=False,
    billing_model="free",
    key_prefix="csk-",
    key_validation="models_list",
    models=("llama3.1-70b", "llama3.1-8b"),
    priority=2,
    docs_url="https://cloud.cerebras.ai",
    logo="cerebras",
)

_SAMBANOVA = ProviderDefinition(
    id="sambanova",
    display_name="SambaNova",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://api.sambanova.ai/v1",
    base_url_editable=False,
    billing_model="free",
    key_prefix="",
    key_validation="models_list",
    models=("Meta-Llama-3.3-70B-Instruct", "DeepSeek-R1-Distill-Llama-70B"),
    priority=2,
    docs_url="https://cloud.sambanova.ai/apis",
    logo="sambanova",
)

_QWEN = ProviderDefinition(
    id="qwen",
    display_name="Qwen Cloud (Alibaba)",
    category="direct",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    base_url_editable=False,
    billing_model="pay_per_use",
    key_prefix="sk-",
    key_validation="models_list",
    models=("qwen-max", "qwen-plus", "qwen-turbo", "qwq-32b"),
    priority=2,
    docs_url="https://bailian.console.alibabacloud.com",
    logo="qwen",
)

# ---------------------------------------------------------------------------
# Gateways — local/self-hosted
# ---------------------------------------------------------------------------

_OLLAMA = ProviderDefinition(
    id="ollama",
    display_name="Ollama",
    category="gateway",
    api_type="openai_compatible",
    auth_type="none",
    default_base_url="http://localhost:11434/v1",
    base_url_editable=True,
    billing_model="self_hosted",
    key_prefix="",
    key_validation="models_list",
    models=(),  # discovered at runtime
    priority=0,
    docs_url="https://ollama.com",
    logo="ollama",
)

_OPENCLAW = ProviderDefinition(
    id="openclaw",
    display_name="OpenClaw",
    category="gateway",
    api_type="openai_compatible",
    auth_type="optional_key",
    default_base_url="http://localhost:18789/v1",
    base_url_editable=True,
    billing_model="subscription",
    key_prefix="",
    key_validation="models_list",
    models=(),  # discovered at runtime
    priority=0,
    docs_url="https://openclaw.ai",
    logo="openclaw",
)

_LM_STUDIO = ProviderDefinition(
    id="lmstudio",
    display_name="LM Studio",
    category="gateway",
    api_type="openai_compatible",
    auth_type="none",
    default_base_url="http://localhost:1234/v1",
    base_url_editable=True,
    billing_model="self_hosted",
    key_prefix="",
    key_validation="models_list",
    models=(),
    priority=0,
    docs_url="https://lmstudio.ai",
    logo="lmstudio",
)

_VLLM = ProviderDefinition(
    id="vllm",
    display_name="vLLM",
    category="gateway",
    api_type="openai_compatible",
    auth_type="optional_key",
    default_base_url="http://localhost:8000/v1",
    base_url_editable=True,
    billing_model="self_hosted",
    key_prefix="",
    key_validation="models_list",
    models=(),
    priority=1,
    docs_url="https://docs.vllm.ai",
    logo="vllm",
)

_LITELLM = ProviderDefinition(
    id="litellm",
    display_name="LiteLLM",
    category="gateway",
    api_type="openai_compatible",
    auth_type="optional_key",
    default_base_url="http://localhost:4000/v1",
    base_url_editable=True,
    billing_model="self_hosted",
    key_prefix="",
    key_validation="models_list",
    models=(),
    priority=1,
    docs_url="https://docs.litellm.ai",
    logo="litellm",
)

_CLOUDFLARE = ProviderDefinition(
    id="cloudflare",
    display_name="Cloudflare AI Gateway",
    category="gateway",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://gateway.ai.cloudflare.com/v1",
    base_url_editable=True,
    billing_model="pay_per_use",
    key_prefix="",
    key_validation="chat_completion",
    models=(),
    priority=2,
    docs_url="https://developers.cloudflare.com/ai-gateway",
    logo="cloudflare",
)

# ---------------------------------------------------------------------------
# Meta-router
# ---------------------------------------------------------------------------

_OPENROUTER = ProviderDefinition(
    id="openrouter",
    display_name="OpenRouter",
    category="meta_router",
    api_type="openai_compatible",
    auth_type="api_key",
    default_base_url="https://openrouter.ai/api/v1",
    base_url_editable=False,
    billing_model="prepaid",
    key_prefix="sk-or-",
    key_validation="models_list",
    models=(),  # 200+ — too many to enumerate
    priority=0,
    docs_url="https://openrouter.ai/keys",
    logo="openrouter",
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

PROVIDER_CATALOG: dict[str, ProviderDefinition] = {
    p.id: p for p in [
        # P0 direct
        _ANTHROPIC, _OPENAI, _GOOGLE, _GROQ,
        # P1 direct
        _DEEPSEEK, _MISTRAL, _XAI, _TOGETHER,
        # P2 direct
        _FIREWORKS, _NVIDIA, _PERPLEXITY, _MOONSHOT,
        _CEREBRAS, _SAMBANOVA, _QWEN,
        # gateways
        _OLLAMA, _OPENCLAW, _LM_STUDIO, _VLLM, _LITELLM, _CLOUDFLARE,
        # meta-router
        _OPENROUTER,
    ]
}


def get_provider(provider_id: str) -> ProviderDefinition | None:
    return PROVIDER_CATALOG.get(provider_id)


def list_providers_by_category(category: str) -> list[ProviderDefinition]:
    return sorted(
        [p for p in PROVIDER_CATALOG.values() if p.category == category],
        key=lambda p: (p.priority, p.display_name),
    )
