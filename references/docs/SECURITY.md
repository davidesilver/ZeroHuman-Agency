# Sicurezza e Compliance

> Requisiti di sicurezza, GDPR, gestione secrets, e best practices per il Content Engine.

---

## 1. Autenticazione e Autorizzazione

### Supabase Auth
- **Metodo:** Email + password (MVP), Google OAuth (futuro)
- **JWT:** Token Supabase con claims custom (`brand_id`, `role`)
- **Sessione:** Refresh token automatico, scadenza 1 ora
- **Logout:** Invalida tutti i token della sessione

### Ruoli Utente

| Ruolo | Permessi |
|-------|----------|
| `owner` | Tutto: CRUD contenuti, config brand, gestione utenti, trigger pipeline, invio newsletter |
| `editor` | Creare/modificare contenuti, approvare, triggerare ricerca. NO config brand, NO gestione utenti |
| `viewer` | Solo lettura: dashboard, metriche, contenuti. NO modifiche |

### Row Level Security (RLS)
- **Ogni tabella** ha policy RLS basata su `brand_id`
- L'utente puo' vedere/modificare SOLO i dati del proprio brand
- Il `service_role` key bypassa RLS per operazioni background (agenti, cron)
- **MAI** esporre il `service_role` key al frontend

```sql
-- Esempio policy RLS
CREATE POLICY "Users can only see their brand data"
ON research_items FOR SELECT
USING (brand_id = (SELECT brand_id FROM users WHERE id = auth.uid()));
```

---

## 2. Gestione Secrets

### Variabili d'Ambiente

**CRITICO:** Le API key NON devono MAI essere:
- Committate nel repository Git
- Esposte nel codice frontend
- Loggate in chiaro
- Condivise via chat/email

### Struttura `.env`

```env
# .env.local (MAI committare — in .gitignore)

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...          # Safe per frontend
SUPABASE_SERVICE_ROLE_KEY=eyJ...              # SOLO backend

# AI Models
OPENROUTER_API_KEY=or-...                     # SOLO backend

# Research
SERPER_API_KEY=...                            # SOLO backend
FIRECRAWL_API_KEY=...                         # SOLO backend
YOUTUBE_API_KEY=...                           # SOLO backend

# Distribution
RESEND_API_KEY=re_...                         # SOLO backend
POSTIZ_API_KEY=...                            # SOLO backend

# Voice (futuro)
ELEVENLABS_API_KEY=...                        # SOLO backend

# Monitoring
SENTRY_DSN=https://...                        # Safe per frontend
```

### Supabase Vault (Produzione)
Per produzione, usare Supabase Vault per secrets:
```sql
-- Salvare secret
SELECT vault.create_secret('openrouter_key', 'or-xxx...', 'OpenRouter API Key');

-- Leggere secret (solo da function/trigger)
SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'openrouter_key';
```

### Rotazione Chiavi
- Ruotare API key ogni 90 giorni
- Supabase JWT secret: non ruotare manualmente (gestito da Supabase)
- OpenRouter: ruotare se sospetto di leak
- Monitorare costi anomali come indicatore di key compromessa

---

## 3. GDPR Compliance

### Obblighi per Newsletter in Italia/EU

| Requisito | Implementazione |
|-----------|----------------|
| **Consenso esplicito** | Double opt-in: email di conferma con link |
| **Diritto di accesso** | Endpoint per scaricare tutti i dati dell'iscritto |
| **Diritto di cancellazione** | Unsubscribe con un click + cancellazione dati entro 30 giorni |
| **Informativa privacy** | Link a privacy policy in ogni email |
| **Base giuridica** | Consenso (Art. 6(1)(a) GDPR) per marketing |
| **Data minimization** | Raccogliere solo email e nome, nient'altro |
| **Record del consenso** | Salvare timestamp, IP, e metodo di consenso |
| **DPO** | Non obbligatorio per PMI < 250 dipendenti |

### Implementazione Double Opt-In

```
1. Utente inserisce email nel form
2. Sistema invia email con link di conferma (token univoco)
3. Utente clicca il link → conferma iscrizione
4. Sistema salva: email, timestamp, IP, consenso=true
5. Solo dopo conferma l'utente riceve newsletter
```

### Footer Email Obbligatorio

Ogni newsletter DEVE includere:
- Nome e indirizzo del mittente (ragione sociale)
- Link "Cancella iscrizione" (unsubscribe)
- Link "Privacy Policy"
- Motivo per cui l'utente riceve l'email

### Cookie Consent (Dashboard Web)
- La dashboard interna non richiede cookie consent (utenti autenticati, no tracking marketing)
- Se si aggiunge Google Analytics o tracking esterno: implementare cookie banner

---

## 4. Sicurezza Applicativa

### OWASP Top 10 — Mitigazioni

| Vulnerabilita' | Mitigazione |
|----------------|-------------|
| **Injection (SQL)** | Supabase client con query parametrizzate. MAI concatenare stringhe SQL. |
| **Broken Auth** | Supabase Auth gestisce sessioni e token. Verificare JWT server-side. |
| **Sensitive Data Exposure** | HTTPS ovunque. API key solo backend. No dati sensibili in URL/log. |
| **XXE** | Non applicabile (no XML parsing). |
| **Broken Access Control** | RLS Supabase per isolamento dati. Middleware Next.js per protezione route. |
| **Security Misconfiguration** | Header sicurezza: CSP, X-Frame-Options, HSTS. Disabilitare directory listing. |
| **XSS** | React escapa automaticamente. Sanitizzare HTML newsletter con DOMPurify. |
| **Insecure Deserialization** | Validare tutti gli input con Zod/Valibot. |
| **Insufficient Logging** | Log strutturati con Sentry. Alerting su errori critici. |
| **SSRF** | Validare URL prima di fetch (no localhost, no internal IPs). |

### Headers di Sicurezza (Next.js)

```typescript
// next.config.ts
const securityHeaders = [
  { key: 'X-DNS-Prefetch-Control', value: 'on' },
  { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
  { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
];
```

### Rate Limiting

| Endpoint | Limite | Finestra |
|----------|--------|----------|
| `POST /api/research/trigger` | 5 | 1 ora |
| `POST /api/content/generate` | 20 | 1 ora |
| `POST /api/newsletter/send` | 2 | 1 giorno |
| `POST /api/scoring/run` | 10 | 1 ora |
| `GET /api/*` (lettura) | 100 | 1 minuto |
| Login | 5 tentativi | 15 minuti (lockout) |

### Validazione Input
- **Tutti** gli input utente validati con Zod schema
- URL: validare formato, bloccare IP private/localhost
- Testo libero: sanitizzare HTML, max length
- File upload: non previsto (contenuti generati, non caricati)

---

## 5. Sicurezza Infrastruttura

### VPS (Hostinger)

```bash
# Checklist sicurezza VPS
- [ ] SSH key-only (disabilitare password login)
- [ ] Firewall (UFW): solo porte 22, 80, 443
- [ ] Fail2ban per protezione brute-force SSH
- [ ] Aggiornamenti automatici sicurezza (unattended-upgrades)
- [ ] Utente non-root per applicazioni
- [ ] Tailscale per comunicazione staging ↔ production
- [ ] Certificato SSL Let's Encrypt (auto-renew)
- [ ] Log rotation configurato
```

### Separazione Staging/Production

| | Staging | Production |
|-|---------|------------|
| Database | Supabase progetto separato | Supabase progetto principale |
| API Keys | Key di test | Key di produzione |
| Dominio | staging.brand.com | brand.com |
| Dati | Dati finti/test | Dati reali |
| Email | Sandbox (no invio reale) | Invio reale |
| Deploy | Push manuale | GitHub → auto deploy |

**REGOLA:** MAI sperimentare in produzione. Ogni modifica passa prima da staging.

---

## 6. Backup e Disaster Recovery

### Backup Automatici
- **Supabase:** backup automatici giornalieri (inclusi nel piano)
- **Codice:** Git repository (GitHub/GitLab) con branch protection
- **Configurazione:** `brand.config.ts` versionato in Git
- **Secrets:** documentati in password manager (1Password/Bitwarden), NON in Git

### Backup Manuale Settimanale
```bash
# Script backup database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
# Upload su Cloudflare R2 o S3
aws s3 cp backup_*.sql s3://brand-backups/
```

### Piano di Recovery

| Scenario | Recovery Time | Procedura |
|----------|--------------|-----------|
| Database corrotto | ~30 min | Restore da backup Supabase |
| VPS down | ~15 min | Redeploy da Git su nuovo VPS |
| API key compromessa | ~5 min | Revocare e rigenerare key |
| Frontend down | ~5 min | Vercel auto-heal, rollback a commit precedente |
| Errore codice in prod | ~10 min | Git revert + redeploy |

---

## 7. Monitoring e Alerting

### Sentry (Error Tracking)
- Cattura errori JavaScript (frontend) e Python (backend)
- Alert su Slack/email per errori critici
- Source maps per debugging frontend

### Health Checks
```
GET /api/health → { status: "ok", db: "connected", agents: "running" }
```
- Monitorare con UptimeRobot o Supabase Edge Function cron
- Alert se endpoint non risponde per > 5 minuti

### Alert Costi
- Se spesa API giornaliera supera `alert_threshold_usd` → notifica
- Se spesa mensile supera budget → pausa agenti non critici
- Dashboard `/costi-api` con visual alert

### Log Strutturati
```json
{
  "timestamp": "2026-04-11T07:00:00Z",
  "level": "info",
  "agent": "research_orchestrator",
  "action": "pipeline_completed",
  "brand_id": "uuid...",
  "items_found": 142,
  "duration_ms": 45000,
  "cost_usd": 0.42
}
```
