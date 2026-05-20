# Architecture — LLM Provider Hub

> Companion to: `docs/plans/2026-05-18-llm-provider-hub-prd.md`
> Status: Draft 2026-05-18

---

## 1. Design Principles

1. **One interface, many backends** — `GenericOpenAIProvider` covers 80%+ of providers. Don't create per-provider classes unless the API is truly different (only Anthropic today).
2. **User keys first, system keys fallback** — the registrar always prefers user BYOK over admin env vars.
3. **Gateways are just providers with editable URLs** — Ollama, OpenClaw, LM Studio use the same `GenericOpenAIProvider` with `base_url_editable=True` and `auth_type="none"` or `"api_key"`.
4. **Secrets never leave Python** — TS layer can check existence but never reads decrypted values. All API calls happen in FastAPI.
5. **Fail open to fallback, fail closed to user** — if BYOK fails, try system key. If nothing works, return an actionable error, never silently degrade quality.

## 2. Component Diagram

```
Browser (Next.js)
│
├── Settings > AI Providers page
│     ├── <ProviderHub />           ← new component
│     │     ├── <BYOKSection />     ← API key CRUD per provider
│     │     ├── <GatewaySection />  ← local gateway config
│     │     ├── <MetaRouterSection /> ← OpenRouter
│     │     └── <RoutingPrefs />    ← provider/model/budget prefs
│     └── <ProviderStatsCard />     ← existing, enhanced
│
├── Setup Wizard > Step "LLM"
│     └── <WizardProviderStep />    ← compact version of ProviderHub
│
└── API Routes (Next.js → FastAPI proxy)
      ├── POST /api/llm/providers/{provider}/key     → save BYOK
      ├── DELETE /api/llm/providers/{provider}/key    → remove BYOK
      ├── POST /api/llm/providers/{provider}/validate → test key
      ├── GET  /api/llm/providers/configured          → list configured
      ├── GET  /api/llm/providers/catalog              → static catalog
      ├── PUT  /api/llm/config                         → save prefs
      ├── GET  /api/llm/config                         → read prefs
      ├── POST /api/llm/gateways/probe                 → health check
      └── GET  /api/llm/providers/metrics              → existing
```

```
FastAPI (Python)
│
├── routes_llm_providers.py        ← enhanced with new endpoints
│
├── services/llm/
│     ├── provider.py              ← LLMProvider ABC (unchanged)
│     ├── provider_catalog.py      ← NEW: ProviderDefinition registry
│     ├── generic_openai.py        ← NEW: GenericOpenAIProvider
│     ├── anthropic_direct.py      ← NEW: AnthropicDirectProvider
│     ├── openrouter.py            ← existing (becomes thin wrapper)
│     ├── openclaw.py              ← existing (migrates to GenericOpenAI)
│     ├── registrar.py             ← enhanced routing logic
│     └── telemetry.py             ← unchanged
│
├── services/brand_secrets.py      ← unchanged (already supports BYOK)
│
└── db tables
      ├── brand_integrations       ← existing (stores encrypted keys)
      ├── brand_llm_config         ← NEW (stores preferences)
      └── llm_provider_metrics     ← existing (telemetry)
```

## 3. Database Changes

### 3.1 New table: `brand_llm_config`

```sql
CREATE TABLE IF NOT EXISTS public.brand_llm_config (
  brand_id            uuid        PRIMARY KEY REFERENCES public.brands(id) ON DELETE CASCADE,
  preferred_provider  text,                    -- 'anthropic' | 'openai' | 'ollama' | null (auto)
  preferred_model     text,                    -- specific model override or null
  fallback_strategy   text        NOT NULL DEFAULT 'auto',  -- 'auto' | 'cheapest' | 'fastest'
  capability_overrides jsonb      NOT NULL DEFAULT '{}',    -- {"creative": "claude-opus-4", "scoring": "gpt-4o-mini"}
  gateway_configs     jsonb       NOT NULL DEFAULT '[]',    -- [{"type":"ollama","url":"http://localhost:11434","enabled":true}]
  daily_budget_usd    numeric(10,4),           -- AI spend cap (null = unlimited)
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.brand_llm_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY brand_llm_config_select ON public.brand_llm_config
  FOR SELECT USING (public.user_has_brand(brand_id));
CREATE POLICY brand_llm_config_insert ON public.brand_llm_config
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));
CREATE POLICY brand_llm_config_update ON public.brand_llm_config
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));
```

### 3.2 Existing tables (no changes needed)

- **`brand_integrations`** — already supports arbitrary `(brand_id, provider, key_name)` tuples with Fernet encryption. BYOK keys stored as `provider='anthropic', key_name='api_key'` etc.
- **`llm_provider_metrics`** — already records provider, model, latency, cost per call. No schema changes.

## 4. Provider Catalog

### 4.1 Data model

```python
@dataclass(frozen=True)
class ProviderDefinition:
    id: str                         # "anthropic", "openai", "ollama"
    display_name: str               # "Anthropic"
    category: str                   # "direct" | "gateway" | "meta_router"
    api_type: str                   # "openai_compatible" | "anthropic_native"
    auth_type: str                  # "api_key" | "none" | "optional_key"
    default_base_url: str           # "https://api.anthropic.com" or "http://localhost:11434/v1"
    base_url_editable: bool         # True for gateways
    billing_model: str              # "pay_per_use" | "subscription" | "free" | "self_hosted" | "prepaid"
    key_prefix: str                 # "sk-ant-" for Anthropic — helps validate format
    key_validation: str             # "models_list" | "chat_completion" | "none"
    models: list[str]               # known models (empty for gateways — discovered at runtime)
    priority: int                   # P0=0, P1=1, P2=2 — controls display order
    docs_url: str                   # link to provider's API key page
    logo_path: str                  # "/providers/anthropic.svg"
```

### 4.2 Registry

```python
PROVIDER_CATALOG: dict[str, ProviderDefinition] = {
    "anthropic": ProviderDefinition(
        id="anthropic",
        display_name="Anthropic",
        category="direct",
        api_type="anthropic_native",
        auth_type="api_key",
        default_base_url="https://api.anthropic.com",
        base_url_editable=False,
        billing_model="pay_per_use",
        key_prefix="sk-ant-",
        key_validation="models_list",
        models=["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-4-20250514"],
        priority=0,
        docs_url="https://console.anthropic.com/settings/keys",
        logo_path="/providers/anthropic.svg",
    ),
    "openai": ProviderDefinition(
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
        models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        priority=0,
        docs_url="https://platform.openai.com/api-keys",
        logo_path="/providers/openai.svg",
    ),
    "groq": ProviderDefinition(
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
        models=["llama-3.3-70b-versatile", "gemma2-9b-it", "mixtral-8x7b-32768"],
        priority=0,
        docs_url="https://console.groq.com/keys",
        logo_path="/providers/groq.svg",
    ),
    "google": ProviderDefinition(
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
        models=["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
        priority=0,
        docs_url="https://aistudio.google.com/apikey",
        logo_path="/providers/google.svg",
    ),
    # --- Gateways ---
    "ollama": ProviderDefinition(
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
        models=[],  # discovered at runtime
        priority=0,
        docs_url="https://ollama.com",
        logo_path="/providers/ollama.svg",
    ),
    "openclaw": ProviderDefinition(
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
        models=[],  # discovered at runtime
        priority=0,
        docs_url="https://openclaw.ai",
        logo_path="/providers/openclaw.svg",
    ),
    "lmstudio": ProviderDefinition(
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
        models=[],
        priority=0,
        docs_url="https://lmstudio.ai",
        logo_path="/providers/lmstudio.svg",
    ),
    # --- Meta-router ---
    "openrouter": ProviderDefinition(
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
        models=[],  # 200+ — fetched from /models
        priority=0,
        docs_url="https://openrouter.ai/keys",
        logo_path="/providers/openrouter.svg",
    ),
    # --- P1 providers ---
    "deepseek": ProviderDefinition(
        id="deepseek",
        display_name="DeepSeek",
        category="direct",
        api_type="openai_compatible",
        auth_type="api_key",
        default_base_url="https://api.deepseek.com/v1",
        base_url_editable=False,
        billing_model="pay_per_use",
        key_prefix="sk-",
        key_validation="chat_completion",
        models=["deepseek-chat", "deepseek-reasoner"],
        priority=1,
        docs_url="https://platform.deepseek.com/api_keys",
        logo_path="/providers/deepseek.svg",
    ),
    "mistral": ProviderDefinition(
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
        models=["mistral-large-latest", "mistral-small-latest", "codestral-latest"],
        priority=1,
        docs_url="https://console.mistral.ai/api-keys",
        logo_path="/providers/mistral.svg",
    ),
    "xai": ProviderDefinition(
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
        models=["grok-3", "grok-3-mini"],
        priority=1,
        docs_url="https://console.x.ai",
        logo_path="/providers/xai.svg",
    ),
    "together": ProviderDefinition(
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
        models=["meta-llama/Llama-3.3-70B-Instruct-Turbo", "Qwen/Qwen2.5-72B-Instruct-Turbo"],
        priority=1,
        docs_url="https://api.together.ai/settings/api-keys",
        logo_path="/providers/together.svg",
    ),
}
```

P2 providers (Fireworks, NVIDIA, Perplexity, Moonshot, Cerebras, SambaNova, Qwen Cloud, vLLM, LiteLLM, Cloudflare) follow the same pattern and are added in Phase 4.

## 5. GenericOpenAIProvider

Single implementation covering all OpenAI-compatible providers:

```python
class GenericOpenAIProvider(LLMProvider):
    """Covers any provider with an OpenAI-compatible chat/completions endpoint."""

    def __init__(self, provider_id: str, base_url: str, api_key: str | None = None):
        self._provider_id = provider_id
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    @property
    def name(self) -> str:
        return self._provider_id

    def complete(self, request: LLMRequest) -> LLMResult:
        # Same pattern as existing OpenClawProvider.complete()
        # but parameterized by base_url and api_key
        ...

    def is_available(self, brand_id: str) -> bool:
        catalog = PROVIDER_CATALOG.get(self._provider_id)
        if not catalog:
            return False
        if catalog.auth_type == "none":
            return True  # gateway, no key needed
        return bool(self._api_key)

    def list_models(self) -> list[str]:
        """GET /models — used for gateway discovery and validation."""
        ...

    @classmethod
    def from_brand_config(cls, provider_id: str, brand_id: str) -> "GenericOpenAIProvider | None":
        """Factory: build from brand_integrations + brand_llm_config."""
        catalog = PROVIDER_CATALOG.get(provider_id)
        if not catalog:
            return None

        # Resolve base_url (custom for gateways, default for direct)
        base_url = _resolve_base_url(brand_id, provider_id, catalog)

        # Resolve API key (BYOK from brand_integrations, or None for auth_type="none")
        api_key = None
        if catalog.auth_type in ("api_key", "optional_key"):
            api_key = get_brand_secret(brand_id, provider_id, "api_key")
            if catalog.auth_type == "api_key" and not api_key:
                return None  # required key missing

        return cls(provider_id, base_url, api_key)
```

## 6. AnthropicDirectProvider

Anthropic's API is not OpenAI-compatible. Uses the official `anthropic` SDK:

```python
class AnthropicDirectProvider(LLMProvider):
    """Anthropic Claude via official SDK (messages API)."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "anthropic"

    def complete(self, request: LLMRequest) -> LLMResult:
        # Uses anthropic.Anthropic(api_key=self._api_key).messages.create(...)
        ...

    @classmethod
    def from_brand_config(cls, brand_id: str) -> "AnthropicDirectProvider | None":
        api_key = get_brand_secret(brand_id, "anthropic", "api_key")
        if not api_key:
            # Fallback to system env var
            api_key = settings.anthropic_api_key
        if not api_key:
            return None
        return cls(api_key)
```

## 7. Enhanced Registrar

The registrar becomes the central routing brain:

```python
class ProviderRegistrar:

    def get_for_brand(
        self,
        brand_id: str,
        task_type: str = "general",
        preferred: str | None = None,
    ) -> LLMProvider:
        """
        Cascade:
        1. Explicit preferred (from arg or brand_llm_config)
        2. Capability override (brand_llm_config.capability_overrides)
        3. BYOK providers (in catalog priority order)
        4. Connected gateways (Ollama, OpenClaw, etc.)
        5. System env var providers
        6. OpenRouter free tier (emergency)
        """
        config = _load_brand_llm_config(brand_id)

        # 1. Explicit preferred
        pref = preferred or (config.preferred_provider if config else None)
        if pref:
            p = _build_provider(pref, brand_id)
            if p:
                return p

        # 2. Capability override
        if config and config.capability_overrides:
            cap_provider = config.capability_overrides.get(task_type)
            if cap_provider:
                p = _build_provider(cap_provider, brand_id)
                if p:
                    return p

        # 3. BYOK providers (sorted by catalog priority)
        for defn in sorted(PROVIDER_CATALOG.values(), key=lambda d: d.priority):
            if defn.category != "direct":
                continue
            p = _build_provider(defn.id, brand_id)
            if p:
                return p

        # 4. Gateways
        if config and config.gateway_configs:
            for gw in config.gateway_configs:
                if gw.get("enabled"):
                    p = _build_gateway_provider(gw, brand_id)
                    if p:
                        return p

        # 5. System fallback (env vars)
        if settings.anthropic_api_key:
            return AnthropicDirectProvider(settings.anthropic_api_key)
        if settings.openrouter_api_key:
            return _system_openrouter()

        # 6. OpenRouter free tier
        return _openrouter_free_tier()
```

## 8. API Routes

### 8.1 New FastAPI endpoints

```
POST   /llm/providers/{provider_id}/key
  Body: { "api_key": "sk-..." }
  → Validates key format (key_prefix), test call, encrypts, saves to brand_integrations.
  → Returns: { "valid": true, "models": ["gpt-4o", ...] }

DELETE /llm/providers/{provider_id}/key
  → Deletes from brand_integrations, invalidates cache.

POST   /llm/providers/{provider_id}/validate
  Body: { "api_key": "sk-..." }  (or empty for gateways)
  → Test call without saving. Returns: { "valid": true, "latency_ms": 340 }

GET    /llm/providers/configured
  → Returns list of providers with BYOK key configured for this brand.
  → Also includes system-level providers from env vars.

GET    /llm/providers/catalog
  → Returns full provider catalog (static, no secrets).

PUT    /llm/config
  Body: { "preferred_provider": "anthropic", "fallback_strategy": "auto", ... }
  → Upserts brand_llm_config.

GET    /llm/config
  → Returns brand_llm_config for active brand.

POST   /llm/gateways/probe
  Body: { "url": "http://localhost:11434/v1" }
  → GET {url}/models — returns available models and latency.
```

### 8.2 Next.js proxy routes

All new endpoints proxied through `src/app/api/llm/` using existing `proxyToBackend()` pattern. Auth via Supabase session token.

## 9. Key Validation Strategy

| Provider | Validation method | Endpoint |
|----------|-------------------|----------|
| OpenAI-compatible (most) | GET /models | Returns model list on success, 401 on invalid key |
| Anthropic | POST /messages with minimal prompt | 1-token completion, checks auth |
| Gateways (Ollama, LM Studio) | GET /v1/models | No auth needed, checks if server is running |
| OpenClaw | GET /v1/models | With or without API key depending on config |

Validation is fast (<2s) and cheap (no token cost for /models calls).

## 10. Migration Path from Current System

### What changes

| Component | Before | After |
|-----------|--------|-------|
| `registrar.py` | Hardcoded OpenRouter + OpenClaw | Dynamic routing from brand_llm_config + catalog |
| `openclaw.py` | Custom httpx implementation | Migrates to `GenericOpenAIProvider` |
| `openrouter.py` | Wraps `call_llm()` | Becomes system fallback, new BYOK uses GenericOpenAI |
| Settings page | Read-only env var status | Interactive Provider Hub |
| Wizard Step "LLM" | Read-only check | BYOK / Gateway config |
| `llm_models.py` | Static MODEL_CONFIGS | Extended with per-provider model lists from catalog |

### What stays the same

- `LLMProvider` ABC interface — unchanged
- `LLMRequest` / `LLMResult` dataclasses — unchanged
- `brand_integrations` table — unchanged, already supports BYOK pattern
- `brand_secrets.py` — unchanged, already has get/set/delete
- `llm_provider_metrics` — unchanged
- `telemetry.py` — unchanged
- `parallel_llm.py` — unchanged
- `call_llm()` in llm_client.py — unchanged (registrar handles routing)
- Cost tracking, rate limiting, degradation — unchanged

### Backward compatibility

- System env vars (`ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`) continue to work as before
- If no BYOK is configured, behavior is identical to current system
- The OpenClaw A/B split feature flag continues to work but is subsumed by the new routing

## 11. Security Invariants

See full compliance document: `docs/plans/2026-05-18-llm-provider-hub-compliance.md`

Summary:
- API keys encrypted at rest (Fernet AES-128-CBC + HMAC-SHA256)
- RLS on all tables — users can only access their brand's data
- TS layer never sees decrypted keys
- Validation endpoints don't persist keys on failure
- Gateway probe only hits localhost/private networks by default (SSRF protection)
- Rate limiting on key validation endpoints to prevent abuse
