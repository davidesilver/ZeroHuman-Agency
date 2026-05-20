# Compliance & Security Check — LLM Provider Hub

> Companion to: `docs/plans/2026-05-18-llm-provider-hub-prd.md`
> Architecture: `docs/plans/2026-05-18-llm-provider-hub-architecture.md`
> Existing security docs: `docs/security/SECRET-ROTATION.md`
> Status: Draft 2026-05-18

---

## 1. Threat Model

### 1.1 Assets to protect

| Asset | Classification | Storage |
|-------|---------------|---------|
| User API keys (BYOK) | Secret — credential | `brand_integrations.encrypted_value` (Fernet ciphertext) |
| System API keys (env var) | Secret — credential | `.env.local`, never in DB |
| Provider preferences | Internal — config | `brand_llm_config` (RLS-protected) |
| LLM call telemetry | Internal — metrics | `llm_provider_metrics` (RLS-protected) |
| Prompt content | PII-adjacent | Transient (not persisted in provider hub) |
| Gateway URLs | Internal — config | `brand_llm_config.gateway_configs` (RLS-protected) |

### 1.2 Threat actors

| Actor | Capability | Goal |
|-------|-----------|------|
| External attacker | Network access to public endpoints | Steal API keys, SSRF via gateway probe |
| Malicious user (multi-tenant) | Authenticated, different brand | Access another brand's keys/config |
| Compromised frontend | XSS or supply chain attack | Exfiltrate keys from API responses |
| Insider (admin) | Server access, env vars | Already has system keys; BYOK keys are per-brand encrypted |

## 2. Security Controls

### 2.1 Encryption at rest

**Status: EXISTING — no changes needed.**

| Property | Value |
|----------|-------|
| Algorithm | Fernet (AES-128-CBC + HMAC-SHA256) |
| Key source | `BRAND_SECRETS_ENCRYPTION_KEY` env var |
| Key size | 32-byte URL-safe base64 |
| Ciphertext location | `brand_integrations.encrypted_value` |
| Plaintext access | Only `brand_secrets.py` in Python process |

**Compliance check:**
- [x] Keys encrypted before DB write (`set_brand_secret()` encrypts first)
- [x] DB stores only ciphertext — DB server never sees plaintext
- [x] Encryption key not in DB, not in code, not in git
- [x] Cache is in-memory only, not persisted to disk
- [x] `invalidate_brand_cache()` clears on key update/delete

**Recommendation:** Rotate `BRAND_SECRETS_ENCRYPTION_KEY` annually. Add rotation procedure to `SECRET-ROTATION.md`.

### 2.2 Row Level Security (RLS)

**Status: EXISTING for `brand_integrations`. NEW table `brand_llm_config` needs RLS.**

| Table | RLS | Policy |
|-------|-----|--------|
| `brand_integrations` | Enabled | `user_has_brand(brand_id)` on SELECT/INSERT/UPDATE/DELETE |
| `brand_llm_config` | **NEW** | Same `user_has_brand(brand_id)` pattern |
| `llm_provider_metrics` | Enabled | `user_has_brand(brand_id)` on SELECT |

**Compliance check:**
- [x] `brand_integrations` — all 4 policies exist (migration 032)
- [ ] `brand_llm_config` — **must add** 3 policies (SELECT, INSERT, UPDATE) in new migration
- [x] `llm_provider_metrics` — SELECT policy exists (migration 034)

**Risk: Cross-tenant key access.** If RLS is misconfigured on `brand_integrations`, User A could read User B's encrypted keys. Mitigated by: (a) Fernet ciphertext is useless without the encryption key, (b) Python layer double-checks brand_id, (c) RLS is tested in integration tests.

### 2.3 API key never reaches TypeScript

**Status: EXISTING pattern. Must be maintained in new endpoints.**

| Layer | Can see plaintext? | Note |
|-------|-------------------|------|
| Browser JS | Never | Keys masked in UI (sk-ant-***) |
| Next.js TS | Never | Proxy only, never reads `encrypted_value` |
| FastAPI Python | Yes (in-memory) | Only during API calls, never logged |
| Supabase DB | Never | Stores ciphertext only |

**New endpoints compliance:**

| Endpoint | Key in request? | Key in response? | Stored? |
|----------|-----------------|------------------|---------|
| POST /providers/{id}/key | Yes (body) | No (returns `valid: bool`) | Yes (encrypted) on success |
| DELETE /providers/{id}/key | No | No | Deleted |
| POST /providers/{id}/validate | Yes (body) | No (returns `valid: bool`) | **No** — test only |
| GET /providers/configured | No | No (returns `exists: bool`) | N/A |
| GET /providers/catalog | No | No | N/A |
| POST /gateways/probe | No (URL only) | No | N/A |

**Critical rule:** The `validate` endpoint receives a key, tests it, and discards it. It must NOT persist the key or log it.

### 2.4 Logging safety

**Must NOT log:**
- API key values (even partially)
- Fernet ciphertext
- Request bodies to `/key` and `/validate` endpoints

**May log:**
- Provider ID, brand ID, success/failure, latency
- Error messages (sanitized — no key fragments)

**Implementation:** Add a `@no_log_body` decorator or use a sanitizing middleware on sensitive endpoints.

### 2.5 SSRF protection on gateway probe

The `POST /llm/gateways/probe` endpoint accepts a URL and makes an HTTP request. This is an SSRF vector.

**Controls:**

| Control | Implementation |
|---------|---------------|
| URL allowlist | Only `http://localhost:*`, `http://127.0.0.1:*`, `http://[::1]:*`, and RFC 1918 private ranges |
| Port range | 1024-65535 (no privileged ports) |
| Protocol | HTTP only (no HTTPS needed for local, no file://, no ftp://) |
| Timeout | 5s hard timeout |
| Response size | Read only first 64KB (enough for /models JSON) |
| No redirects | `follow_redirects=False` in httpx |
| Path restriction | Only `/v1/models` and `/api/tags` (Ollama native) allowed |

**Blocked examples:**
- `http://169.254.169.254/latest/meta-data/` — AWS IMDS → blocked (link-local)
- `http://internal-service:8080/admin` — → blocked (non-local hostname)
- `file:///etc/passwd` — → blocked (wrong protocol)
- `http://localhost:22` — → blocked (privileged port)

**If cloud-hosted (future):** gateway probe must be disabled entirely or restricted to private VPC ranges.

### 2.6 Rate limiting on key endpoints

**Controls:**

| Endpoint | Rate limit | Why |
|----------|-----------|-----|
| POST /providers/{id}/key | 10/min per brand | Prevent key enumeration |
| POST /providers/{id}/validate | 10/min per brand | Prevent key testing abuse |
| POST /gateways/probe | 20/min per brand | Prevent SSRF amplification |
| DELETE /providers/{id}/key | 5/min per brand | Prevent denial of service |

Uses existing `llm_rate_limiter.py` infrastructure.

### 2.7 Input validation

| Field | Validation | Max length |
|-------|-----------|-----------|
| `api_key` | Non-empty string, no whitespace, optional prefix check | 256 chars |
| `provider_id` | Must exist in PROVIDER_CATALOG | 64 chars |
| `base_url` (gateway) | Must parse as valid URL, pass SSRF checks | 512 chars |
| `preferred_provider` | Must exist in PROVIDER_CATALOG or null | 64 chars |
| `preferred_model` | Alphanumeric + `/` + `-` + `.` + `:` | 128 chars |
| `capability_overrides` | Keys must be valid ModelCapability enum values | 1KB JSON |
| `daily_budget_usd` | Positive number or null | N/A |

## 3. Data Privacy

### 3.1 What data flows to LLM providers

| Data | Flows to provider? | Controllable? |
|------|-------------------|---------------|
| Prompt content | Yes | User chooses provider; local gateways = no external flow |
| System prompt | Yes | Same as above |
| Brand context (tone rules) | Yes (embedded in system prompt) | Same |
| API key | Yes (as Bearer token) | User's own key |
| User PII (email, name) | No | Never included in LLM calls |
| Brand analytics | No | Stays in our DB |

### 3.2 Local-first option

Users who select Ollama or LM Studio as preferred provider get **zero data exfiltration** — all inference happens on their machine. This is a key selling point for privacy-conscious users and should be highlighted in the UI.

### 3.3 Provider data retention policies

We do NOT control what providers do with prompt data. The UI should include a disclaimer:

> "When using cloud providers, your prompts are sent to their servers and subject to their data retention policies. For maximum privacy, use a local gateway (Ollama, LM Studio)."

Link to each provider's data policy from the catalog (`docs_url`).

## 4. GDPR / Data Protection Considerations

| Requirement | Status |
|-------------|--------|
| Data minimization | Prompts sent to providers are task-specific, no unnecessary PII |
| Right to erasure | `DELETE /providers/{id}/key` removes key; brand deletion cascades via FK |
| Data portability | Not applicable (API keys are the user's own credentials) |
| Consent | User explicitly enters key and chooses provider — informed consent |
| Data processing record | `llm_provider_metrics` records which provider was used (no prompt content) |
| Cross-border transfer | Depends on provider choice — Ollama/local = no transfer |

## 5. Secret Rotation for BYOK Keys

**New section to add to `docs/security/SECRET-ROTATION.md`:**

### Per-Brand BYOK Keys (brand_integrations)

BYOK keys are owned by the user. Rotation is user-initiated:

1. User generates new key on provider's console
2. User enters new key in Settings > AI Providers
3. `set_brand_secret()` overwrites ciphertext, invalidates cache
4. Old key should be revoked on provider's console

**System-initiated rotation triggers:**
- Provider reports key as invalid (401 response) → notify user via UI banner
- Periodic health check detects key failure → flag in `brand_llm_config`

### BRAND_SECRETS_ENCRYPTION_KEY rotation

More complex — affects all encrypted values:

1. Generate new Fernet key
2. Run migration script: decrypt all values with old key, re-encrypt with new key
3. Update env var
4. Restart backend

**Recommendation:** Build a `rotate-encryption-key` management command for this.

## 6. Compliance Checklist Summary

| # | Check | Status | Action needed |
|---|-------|--------|---------------|
| 1 | API keys encrypted at rest (Fernet) | PASS | None |
| 2 | RLS on brand_integrations | PASS | None |
| 3 | RLS on brand_llm_config | FAIL | Add in migration |
| 4 | TS layer never sees plaintext keys | PASS | Maintain in new endpoints |
| 5 | Validate endpoint doesn't persist keys | N/A | Implement correctly |
| 6 | No key values in logs | N/A | Add @no_log_body decorator |
| 7 | SSRF protection on gateway probe | N/A | Implement URL allowlist |
| 8 | Rate limiting on key endpoints | N/A | Configure rate limiter |
| 9 | Input validation on all fields | N/A | Implement |
| 10 | Gateway probe restricted to localhost/private | N/A | Implement |
| 11 | Privacy disclaimer in UI | N/A | Add to Provider Hub |
| 12 | Secret rotation documented | PARTIAL | Extend SECRET-ROTATION.md |
| 13 | Cascade delete on brand removal | PASS | FK ON DELETE CASCADE exists |
| 14 | Health check detects key failure | N/A | Implement periodic check |

## 7. Open Questions

1. **Encryption upgrade**: Current Fernet uses AES-128-CBC. Should we upgrade to AES-256-GCM (requires custom implementation, breaks Fernet compatibility)? Recommendation: stay with Fernet for now — it's battle-tested and the key length is adequate for API keys.

2. **Key sharing across brands**: Should a user be allowed to share an API key across multiple brands? Current schema supports it (one row per brand+provider). Recommendation: keep per-brand isolation — simpler, safer, users can paste the same key twice.

3. **Admin visibility into user BYOK**: Should the admin be able to see which brands have BYOK configured (without seeing the keys)? Recommendation: yes — add a read-only admin endpoint that returns `(brand_id, provider, exists, updated_at)`.

4. **Gateway probe in cloud deployment**: If ZeroHuman is cloud-hosted, gateway probe to localhost makes no sense. Should we disable it based on an env var (`DEPLOYMENT_MODE=cloud`)? Recommendation: yes.
