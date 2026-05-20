# Secret Rotation

**Classification**: internal operations document

This procedure covers secret rotation for the project without assuming any specific hosting vendor.

## Pre-Rotation Checklist

- notify the team of possible brief disruption
- verify a non-production environment is available for validation
- prepare a change record for the rotation
- confirm access to every provider console involved in the rotation

## 1. Database Service Key

Rotate when:

- on a fixed schedule
- after suspected exposure
- after environment cloning or credential sharing mistakes

Steps:

```bash
# Update local environment
SUPABASE_SERVICE_ROLE_KEY=<new-value>

# Flush backend auth cache
curl -X POST http://localhost:8000/api/auth/cache-invalidate \
  -H "X-Scheduler-Secret: $SCHEDULER_SECRET"
```

After rotation:

- update the secret in every deployed environment
- restart the backend if required by the host

## 2. Scheduler Secret

Rotate when:

- on a fixed schedule
- after accidental exposure in logs, shells, or CI output

Generate a new value:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Apply it everywhere:

```bash
SCHEDULER_SECRET=<new-value>
```

Then update every scheduler caller that invokes protected endpoints.

## 3. Brand Secrets Encryption Key (Fernet)

Rotate when:

- on a fixed schedule (annually or after team changes)
- after suspected exposure of the key itself
- when re-keying is required for compliance

**Warning**: rotating this key requires re-encrypting every row in `brand_integrations` and `brand_service_credentials`. Do this during a maintenance window.

Steps:

```bash
# 1. Generate a new Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Run the re-encryption script (decrypt with old key, re-encrypt with new key)
cd python
BRAND_SECRETS_ENCRYPTION_KEY_OLD=<old-value> \
BRAND_SECRETS_ENCRYPTION_KEY=<new-value> \
uv run python -m content_engine.utils.rekey_brand_secrets
```

The `rekey_brand_secrets` utility reads every encrypted row, decrypts with the old key, and writes back encrypted with the new key in a single transaction.

```bash
# 3. Update the key in every deployed environment
BRAND_SECRETS_ENCRYPTION_KEY=<new-value>

# 4. Restart the backend
```

After rotation validate that brand-specific API calls (Brevo sync, Heygen video job, etc.) still succeed for at least one brand.

## 4. External Provider Keys

Examples used by the project:

- `SERPER_API_KEY`
- `RESEND_API_KEY`
- `OPENROUTER_API_KEY`
- `ANTHROPIC_API_KEY`
- `POSTIZ_API_KEY`

For each one:

1. generate or issue the replacement credential
2. update local and deployed environments
3. validate one real call
4. revoke the old credential

## 4. Cache Invalidation Endpoint

When database auth-related secrets change, clear the backend JWT cache immediately:

```bash
curl -X POST http://localhost:8000/api/auth/cache-invalidate \
  -H "X-Scheduler-Secret: $SCHEDULER_SECRET"
```

Expected response:

```json
{ "success": true, "data": { "cleared_entries": 42 } }
```

## Post-Rotation Checklist

- backend starts correctly
- `GET /health/db` succeeds
- one authenticated end-to-end call succeeds
- the change record is updated with the rotation date

## Recommended Rotation Register

Track at least:

- secret name
- last rotation date
- next due date
- owner
- validation status
