# Secret Rotation — Procedura Operativa

**Ultima revisione**: 2026-04-13
**Owner**: Platform Team
**Classification**: INTERNAL

> [!IMPORTANT]
> Ruotare i secret è un'operazione critica. Seguire questa checklist nell'ordine esatto.
> Un errore può causare downtime del servizio o esporre le credenziali durante la transizione.

---

## Checklist Pre-Rotazione

- [ ] Avvisare il team via Slack/email (possibile breve downtime durante la rotazione)
- [ ] Verificare che l'ambiente di staging sia aggiornato (per testare prima)
- [ ] Aprire una PR vuota con il titolo "chore: secret rotation YYYY-MM-DD"
- [ ] Avere accesso al pannello di gestione del provider (Supabase, Resend, Serper, etc.)

---

## 1. Supabase Service Role Key

**Quando ruotare**: ogni 90 giorni, o se sospetti una compromissione.

```bash
# 1. Genera nuova chiave nel pannello Supabase
#    Settings → API → service_role key → Rotate

# 2. Aggiorna .env.local
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# 3. Aggiorna le variabili d'ambiente in produzione
#    (Vercel Dashboard → Settings → Environment Variables)

# 4. Invalida la cache JWT del backend Python
curl -X POST http://localhost:8000/api/auth/cache-invalidate \
  -H "X-Scheduler-Secret: $SCHEDULER_SECRET"

# 5. Restart del backend Python
#    (se non usa hot-reload)
```

---

## 2. Scheduler Secret (X-Scheduler-Secret)

**Quando ruotare**: ogni 180 giorni, o se il secret è apparso in log/output.

```bash
# 1. Genera un nuovo secret sicuro
python3 -c "import secrets; print(secrets.token_hex(32))"
# oppure
openssl rand -hex 32

# 2. Aggiorna .env.local e l'ambiente di produzione
SCHEDULER_SECRET=<nuovo-valore>

# 3. Aggiorna anche il job GitHub Actions o il cron che chiama l'endpoint
#    (aggiorna il secret in Settings → Secrets → Actions)

# 4. Restart del backend Python per caricare il nuovo valore
```

---

## 3. API Keys Esterne (Serper, Resend, OpenRouter)

**Quando ruotare**: ogni 90 giorni, o dopo un incidente.

```bash
# Genera nuova chiave nel pannello del provider
# Aggiorna .env.local:
SERPER_API_KEY=<nuova-chiave>
RESEND_API_KEY=<nuova-chiave>
OPENROUTER_API_KEY=<nuova-chiave>

# Aggiorna le variabili d'ambiente in produzione
# Verifica che le nuove chiavi funzionino prima di comunicare la rotazione al team
```

---

## 4. Postiz API Key

```bash
# Postiz → Settings → API Keys → Revoke + Generate new

POSTIZ_API_KEY=<nuova-chiave>
```

---

## 5. Endpoint di Cache Invalidation (L-02)

Quando cambi `SUPABASE_ANON_KEY` o `SUPABASE_SERVICE_ROLE_KEY`, il backend
mantiene in cache le validazioni JWT per 5 minuti (`_AUTH_CACHE` in `auth_middleware.py`).
Per forzare il flush immediato:

```bash
curl -X POST http://localhost:8000/api/auth/cache-invalidate \
  -H "X-Scheduler-Secret: $SCHEDULER_SECRET"

# Risposta attesa:
# {"success": true, "data": {"cleared_entries": 42}}
```

---

## Checklist Post-Rotazione

- [ ] Verificare che il backend Python si avvii correttamente
- [ ] Eseguire `GET /health/db` per verificare la connessione al DB
- [ ] Verificare che almeno una chiamata API end-to-end funzioni (es. `GET /api/research/items`)
- [ ] Aggiornare il documento con la data di rotazione
- [ ] Chiudere la PR aperta in fase di pre-rotazione

---

## Calendario di Rotazione

| Secret | Frequenza | Ultimo rinnovo |
|--------|-----------|----------------|
| `SUPABASE_SERVICE_ROLE_KEY` | 90 giorni | 2026-04-13 |
| `SCHEDULER_SECRET` | 180 giorni | 2026-04-13 |
| `SERPER_API_KEY` | 90 giorni | 2026-04-13 |
| `RESEND_API_KEY` | 90 giorni | 2026-04-13 |
| `OPENROUTER_API_KEY` | 90 giorni | 2026-04-13 |
| `POSTIZ_API_KEY` | 90 giorni | 2026-04-13 |
