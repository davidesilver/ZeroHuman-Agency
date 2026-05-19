# Plan: LLM Provider Hub

> Source PRD: `docs/plans/2026-05-18-llm-provider-hub-prd.md`
> Architecture: `docs/plans/2026-05-18-llm-provider-hub-architecture.md`
> Compliance: `docs/plans/2026-05-18-llm-provider-hub-compliance.md`

## Architectural decisions

- **Routes**: All new FastAPI endpoints under `/llm/` prefix. Next.js proxies via `src/app/api/llm/**`.
- **Schema**: New table `brand_llm_config` (migration 043) for preferences. Existing `brand_integrations` for encrypted BYOK keys — no schema changes.
- **Key models**: `ProviderDefinition` (catalog metadata), `GenericOpenAIProvider` (all OpenAI-compatible), `AnthropicDirectProvider` (Anthropic SDK native).
- **Auth**: All endpoints require Supabase JWT → Python extracts `brand_id` from `request.state`.
- **Encryption**: BYOK keys stored via existing `brand_secrets.py` (Fernet AES). TS layer never sees plaintext.
- **SSRF**: Gateway probe restricted to localhost/RFC-1918 only.
- **Settings sub-page**: `src/app/(dashboard)/settings/ai-providers/page.tsx` — linked from root settings page.

---

## Phase 1: Provider Catalog + Core Provider Classes

**User stories**: foundation for all

### What to build

A static Python catalog (`provider_catalog.py`) describing every supported provider's metadata — id, display name, API type, auth type, default URL, billing model, known models. Two provider implementations: `GenericOpenAIProvider` (covers all OpenAI-compatible APIs) and `AnthropicDirectProvider` (Anthropic SDK). The existing `OpenClawProvider` migrates to a thin wrapper over `GenericOpenAIProvider`. All P0+P1+P2 providers in catalog.

### Acceptance criteria

- [ ] `provider_catalog.py` contains all P0 (Anthropic, OpenAI, Google, Groq), P1 (DeepSeek, Mistral, xAI, Together), P2 (Fireworks, NVIDIA, Perplexity, Moonshot, Cerebras, SambaNova, Qwen) direct providers plus all gateways (Ollama, OpenClaw, LM Studio, vLLM, LiteLLM) and meta-router (OpenRouter)
- [ ] `GenericOpenAIProvider.complete()` works with any OpenAI-compatible base_url + optional api_key
- [ ] `AnthropicDirectProvider.complete()` uses official `anthropic` SDK
- [ ] `GET /llm/providers/catalog` returns the full provider list (no secrets)
- [ ] `llm_models.py` MODEL_CONFIGS extended with all provider models
- [ ] Existing OpenRouter + OpenClaw paths continue to work (zero regression)

---

## Phase 2: BYOK Key Management — Backend + Settings UI

**User stories**: US-1

### What to build

Full CRUD for per-brand API keys: save (encrypted), validate (test call without persisting), delete. A new Settings sub-page `ai-providers` with three sections — BYOK cards for all P0 providers, gateway stubs (collapsed), system fallback status.

### Acceptance criteria

- [ ] `POST /llm/providers/{provider_id}/key` — validates format, test call, encrypts, saves to `brand_integrations`
- [ ] `DELETE /llm/providers/{provider_id}/key` — removes and invalidates cache
- [ ] `POST /llm/providers/{provider_id}/validate` — test call, returns `{valid, latency_ms}`, does NOT persist
- [ ] `GET /llm/providers/configured` — returns providers with keys configured (no values)
- [ ] Next.js proxy routes for all four endpoints
- [ ] `src/app/(dashboard)/settings/ai-providers/page.tsx` renders BYOK section with P0 providers
- [ ] Key entry: masked input + "Test" button + status badge + delete button
- [ ] Link from main settings page to new sub-page
- [ ] API keys logged at no point (even on error)

---

## Phase 3: DB Migration + Enhanced Registrar

**User stories**: US-4

### What to build

Migration 043 creates `brand_llm_config` with preferred_provider, capability_overrides, gateway_configs, daily_budget_usd. Enhanced `ProviderRegistrar.get_for_brand()` implements the 7-level cascade: explicit preferred → capability override → BYOK providers → gateways → system env → OpenRouter free. Config read/write endpoints.

### Acceptance criteria

- [ ] `supabase/migrations/043_brand_llm_config.sql` runs cleanly with RLS (3 policies)
- [ ] `PUT /llm/config` saves preferences for active brand
- [ ] `GET /llm/config` returns preferences
- [ ] Registrar routes to BYOK provider when key is configured for brand
- [ ] Registrar falls back to system env var when no BYOK configured
- [ ] Capability override in `brand_llm_config` affects model selection in `call_llm()`
- [ ] Routing preferences UI section in `ai-providers` page (preferred provider dropdown, fallback strategy)

---

## Phase 4: Gateway Support

**User stories**: US-2, US-3

### What to build

Gateway probe endpoint (`POST /llm/gateways/probe`) hits `/v1/models` on the given URL with SSRF protection (localhost/private only). Gateway section in UI shows Ollama, OpenClaw, LM Studio with auto-detected status. User can set custom URL, enable/disable each gateway. Gateways with configured URL get added to `brand_llm_config.gateway_configs`.

### Acceptance criteria

- [ ] `POST /llm/gateways/probe` with `{url}` — returns `{online, models[], latency_ms}` or `{online: false, error}`
- [ ] SSRF: rejects non-localhost, non-RFC1918, link-local, privileged ports (<1024)
- [ ] `GET /llm/gateways/auto-discover` probes default ports for Ollama (11434), OpenClaw (18789), LM Studio (1234)
- [ ] Gateway section in UI: shows each gateway with status indicator and "Configure" panel
- [ ] Saving gateway URL+enabled writes to `brand_llm_config.gateway_configs`
- [ ] If gateway is preferred and offline, registrar falls back gracefully with log warning

---

## Phase 5: Wizard Step "LLM" Refactor

**User stories**: US-5

### What to build

Replace the read-only wizard Step 1 ("LLM") with an interactive version. Four options: (a) enter a BYOK key, (b) connect Ollama, (c) connect OpenClaw, (d) admin already configured. Provider selector dropdown for option (a). Key validation inline. Step unblocks once any provider is working — either BYOK/gateway configured or system env present.

### Acceptance criteria

- [ ] Wizard Step 1 has four radio options as described
- [ ] Option (a): provider selector + key input + "Test" button — on success shows provider name and model count
- [ ] Option (b/c): URL input + "Test connection" — on success shows model count
- [ ] Option (d): shows system env status (read-only, existing behavior)
- [ ] "Next" is enabled if: any option tested successfully OR system env is present
- [ ] Wizard state survives page reload (existing localStorage persistence)
- [ ] Provider configured in wizard is reflected immediately in the hub settings page

---

## Phase 6+7: Extended Provider Catalog

**User stories**: US-1 extended

### What to build

All P1 and P2 direct providers available in the BYOK section behind a "Show more providers" disclosure. Same GenericOpenAIProvider pattern — only catalog entries and UI cards needed. Model configs for all new providers added to `llm_models.py` MODEL_ROUTING.

### Acceptance criteria

- [ ] P1 providers (DeepSeek, Mistral, xAI, Together) visible and configurable in BYOK section under "Show more"
- [ ] P2 providers (Fireworks, NVIDIA NIM, Perplexity, Moonshot/Kimi, Cerebras, SambaNova, Qwen Cloud) visible under further "Show all"
- [ ] Gateway providers (vLLM, LiteLLM, Cloudflare AI Gateway) in gateway section
- [ ] All provider models present in MODEL_CONFIGS and reachable via capability routing
- [ ] `GET /llm/providers/catalog` returns all providers with category/priority
- [ ] UI search/filter by name in expanded provider list

---

## Phase 8: Cost Dashboard + Budget Alerts

**User stories**: US-6

### What to build

Enhanced ProviderStatsCard with bar chart (cost/1k tokens per provider), per-capability cost breakdown, and budget alert at 80% of daily cap. Budget enforcement: `call_llm()` checks remaining daily budget before calling external providers.

### Acceptance criteria

- [ ] ProviderStatsCard shows bar chart for cost/1k tokens comparison across providers
- [ ] Budget section shows today's spend vs daily cap with progress bar
- [ ] Alert banner appears when daily spend ≥ 80% of cap
- [ ] `call_llm()` rejects calls (returns error) when daily budget is exhausted
- [ ] Budget resets at midnight UTC (leverages existing cost_tracker.py)
- [ ] Cost per capability breakdown table (7 capabilities × top 3 providers)
