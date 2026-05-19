# Plan: Universal Setup Wizard (CLI + Dashboard + Bootstrap)

> Source PRD: `docs/plans/2026-05-19-universal-setup-wizard-prd.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Routes**:
  - `/bootstrap` — new `(bootstrap)` route group, NO auth, NO Supabase deps, NO `(dashboard)` layout
  - `/setup` — existing `(dashboard)` route group, requires auth, expanded from 6 to 10 steps
  - `/api/bootstrap/test-connection` (POST) — active ONLY when Supabase not configured, 403 otherwise
  - `/api/bootstrap/save-config` (POST) — same guard, writes `.env.local` atomically
  - `/api/mcp/detect` (GET) — parallel probe of known MCP server endpoints, 2s timeout

- **Schema**:
  - `setup_progress` table: `brand_id uuid PK → brands(id)`, `completed jsonb` (e.g. `{"llm": true, "brand": true, "voice": false}`), `wizard_state jsonb` (transient form data), `dismissed boolean DEFAULT false`, `created_at`, `updated_at`. RLS via `user_has_brand(brand_id)`.
  - No new tables beyond `setup_progress`. BYOK keys continue using `brand_integrations`. Brand config continues using `brand_llm_config`.

- **CLI**:
  - Location: `cli/` subdirectory with its own `package.json` (`@zerohuman/cli`, `"bin": { "zh": "./dist/index.js" }`)
  - Runtime: Node.js (already required for Next.js)
  - Libraries: `commander` (command routing), `@clack/prompts` (interactive prompts), `chalk` (colors), `ora` (spinners), `dotenv` (env reading)
  - Entry: `cli/src/index.ts`, compiled to `cli/dist/index.js`
  - Root `package.json` adds script: `"zh": "node cli/dist/index.js"`

- **Middleware guard**: `updateSession()` in the Supabase middleware checks `process.env.NEXT_PUBLIC_SUPABASE_URL`. Missing or empty → redirect to `/bootstrap`. Paths `/bootstrap`, `/api/bootstrap/*`, and static assets are excluded from the redirect.

- **Env writer**: reads existing `.env.local`, merges new key-value pairs, writes to `.env.local.tmp`, then `fs.renameSync()` for atomic swap. Shared between CLI and bootstrap API.

- **Python backend degraded mode**: when `NEXT_PUBLIC_SUPABASE_URL` is empty, the Settings model accepts it (change from required to optional with empty default). Only `/health` responds normally. All other routes return `503 Setup Required`.

- **Logo**: Verified Knot rendered as ASCII art with Braille Unicode blocks in CLI. SVG version in bootstrap page and wizard header.

---

## Phase 1: Bootstrap Mode

**User stories**: US-01, US-04

### What to build

Make the app bootable even with zero configuration. The Next.js middleware detects missing `NEXT_PUBLIC_SUPABASE_URL` and redirects every route to `/bootstrap`. The bootstrap page lives in a new `(bootstrap)` route group — completely outside the dashboard layout, with no Supabase client imports, no auth checks.

The page shows the Verified Knot SVG logo, a short explanation, and two options: (A) CLI instructions with a `npx @zerohuman/cli init` copyable command, and (B) a collapsible "Advanced: enter credentials manually" form with three fields (Supabase URL, anon key, service role key). The form hits two new API routes: `POST /api/bootstrap/test-connection` (probes Supabase with the provided credentials) and `POST /api/bootstrap/save-config` (writes `.env.local` atomically). Both endpoints refuse to operate (403) when Supabase is already configured.

The Python backend also changes: `NEXT_PUBLIC_SUPABASE_URL` becomes optional (empty default). When empty, only `/health` responds. All protected routes return 503 with a JSON body `{"detail": "Setup required — run zh init or visit /bootstrap"}`.

End-to-end demo: clone repo → `npm run dev` → open browser → see bootstrap page → enter Supabase creds → test connection → save → restart → see login page.

### Acceptance criteria

- [ ] App starts without crash when `.env.local` is missing or has no Supabase URL
- [ ] Every route redirects to `/bootstrap` when Supabase URL is absent
- [ ] `/bootstrap` page renders: logo, CLI instructions with copy button, collapsible manual form
- [ ] `POST /api/bootstrap/test-connection` validates Supabase credentials (returns success/error with details)
- [ ] `POST /api/bootstrap/save-config` writes `.env.local` atomically via temp-file rename
- [ ] Both bootstrap API endpoints return 403 if Supabase is already configured
- [ ] Python backend starts with empty Supabase URL; `/health` returns 200; all other routes return 503
- [ ] After saving config and restarting, the normal auth flow works (redirect to `/login`)

---

## Phase 2: CLI Scaffold + `zh init` + `zh doctor`

**User stories**: US-02, US-03, US-05

### What to build

A Node.js CLI tool in `cli/` that replaces `setup.sh`. The scaffold uses `commander` for subcommand routing and `@clack/prompts` for interactive input. The Verified Knot ASCII logo displays on `zh init` and `zh doctor`.

`zh init` walks the user through 8 interactive steps:
1. Environment detection (Node, Python, uv, Docker versions)
2. Supabase credentials (cloud project URL + keys, or detect existing `.env.local`)
3. LLM provider — at least one required. Show categorized list from the provider catalog, prompt key, validate prefix, test via HTTP (models list or chat completion), show latency + model count on success.
4. Auto-generate encryption keys (Fernet for brand secrets, hex32 for scheduler secret)
5. Optional services (Serper, Tavily, YouTube, Resend, Replicate, Postiz — each skippable)
6. Write `.env.local` atomically with preview (secrets masked)
7. Database: run Supabase migrations + seed agent system
8. Health check: test all configured services in parallel, display status table

Non-interactive mode: `zh init --supabase-url=... --anthropic-key=... --yes` for CI/CD.

`zh doctor` reads `.env.local`, checks all connections (Supabase DB, Supabase Auth, Python backend, each LLM provider, research APIs, local gateways), reports environment versions, migration status, and an overall readiness verdict.

End-to-end demo: `npx tsx cli/src/index.ts init` → follow prompts → `.env.local` appears → `npm run dev` → app boots to login.

### Acceptance criteria

- [ ] `cli/` directory with `package.json`, `tsconfig.json`, source files compiles without errors
- [ ] `zh init` interactive mode: walks through all 8 steps with validation at each
- [ ] `zh init` non-interactive mode: accepts flags for all required values, skips prompts
- [ ] `zh init` validates Supabase connection before proceeding past step 2
- [ ] `zh init` validates at least one LLM provider key (prefix + HTTP test) before proceeding past step 3
- [ ] `zh init` auto-generates `BRAND_SECRETS_ENCRYPTION_KEY` (Fernet) and `SCHEDULER_SECRET` (hex32)
- [ ] `zh init` writes `.env.local` atomically (temp file → rename), preserving existing values with merge confirmation
- [ ] `zh init` runs Supabase migrations and seed if database step is not skipped
- [ ] `zh doctor` displays environment info, config status, connection tests, migration status, and overall verdict
- [ ] Verified Knot ASCII logo renders correctly on `zh init` and `zh doctor`
- [ ] Root `package.json` has `"zh"` script pointing to CLI entry

---

## Phase 3: Wizard Core (Steps 0–3)

**User stories**: US-11, US-12, US-14, US-15

### What to build

Replace the existing 6-step wizard at `/setup` with the new 10-step architecture. This phase delivers the first 4 steps (all required) plus server-side progress persistence.

A new migration creates the `setup_progress` table. The wizard reads/writes progress via API endpoints (`GET /api/setup/progress`, `PATCH /api/setup/progress`) instead of localStorage only.

**Step 0 — Infrastructure Check**: auto-runs on mount. Probes Python backend (`/health`), Supabase (via a lightweight query), migration status. Shows green/red per check. Blocks progress if critical failures; shows fix instructions (e.g. "Run `zh migrate`").

**Step 1 — LLM Providers**: shows all 22+ providers from `PROVIDER_CATALOG`, grouped by category (P0 always visible, P1/P2 collapsible, gateways with auto-discover, meta-routers). Each provider expands for inline key entry (existing `InlineKeyEntry` pattern). Multiple providers can be configured. Auto-discover button probes local gateway ports. Must configure at least one to proceed.

**Step 2 — Brand Identity**: extends current brand creation with: description field, website URL, logo upload (drag-and-drop → `POST /api/brands/{id}/assets`), primary color picker (saved as palette asset), daily budget. If a brand already exists, shows it and allows "Create another".

**Step 3 — Brand Voice**: reuses the existing `BrandDiscovery` component with its three paths (auto-discover, template, manual). No changes needed to the component itself.

The step indicator expands to 10 steps with labels. Navigation persists: closing the wizard and returning resumes at the last step via `setup_progress`.

End-to-end demo: open `/setup` → infrastructure green → add Anthropic + Groq → create brand "Acme" with logo → discover voice from URLs → progress saved in DB → close tab → reopen → wizard resumes at step 3.

### Acceptance criteria

- [ ] Migration creates `setup_progress` table with RLS policies
- [ ] Step indicator shows 10 steps with correct labels
- [ ] Step 0 checks backend health, Supabase connection, and migration status
- [ ] Step 0 blocks with clear instructions if critical checks fail
- [ ] Step 1 shows all providers from catalog grouped by category (P0, P1/P2, gateways, meta-routers)
- [ ] Step 1 supports configuring multiple providers; at least one required
- [ ] Step 1 gateway auto-discover probes localhost ports and shows results
- [ ] Step 2 includes description, website URL, logo upload, color picker, budget
- [ ] Step 2 allows creating a new brand or editing an existing one
- [ ] Step 3 reuses `BrandDiscovery` component unchanged
- [ ] Progress persists server-side: closing and reopening the wizard resumes at last step
- [ ] "Skip for now" works on Step 3 (voice)

---

## Phase 4: Wizard Optional Steps (4–7)

**User stories**: US-13, US-16, US-17

### What to build

Four new wizard steps, all optional with "Skip for now →" buttons.

**Step 4 — Research Tools**: displays current tier (Free/Tavily/Premium). Inline key entry for Serper, Tavily, YouTube Data API. As keys are saved, the displayed tier upgrades in real time. Shows what each tier unlocks.

**Step 5 — Image Generation**: shows available backends. If OpenAI key was configured in Step 1, DALL-E 3 appears auto-detected. Stability AI and Replicate: key entry + validation. Optional "Test generation" button that creates a sample image.

**Step 6 — Email & Notifications**: radio selection between email providers (Resend, Brevo, SendGrid). Key entry + from name + from email address configuration. "Send test email" button that sends to the current user's email. Telegram bot section: token + chat ID + test message. All saved to `.env.local` via backend API or to `brand_integrations` as brand secrets.

**Step 7 — Social Publishing**: probes Postiz health endpoint. If not running: shows setup instructions (Docker or cloud). If running: shows platform list (13 platforms). For each platform: paste Postiz Integration ID. Tests connection status.

Each step updates `setup_progress.completed` on completion or skip.

End-to-end demo: Step 4 → add Serper key → tier upgrades from Free to Premium → Step 5 → DALL-E auto-detected → skip Stability → Step 6 → configure Resend → test email arrives → Step 7 → Postiz running → add LinkedIn integration.

### Acceptance criteria

- [ ] Step 4 shows current research tier and upgrades live as keys are added
- [ ] Step 4 inline key entry for Serper, Tavily, YouTube with validation
- [ ] Step 5 auto-detects DALL-E if OpenAI key exists from Step 1
- [ ] Step 5 supports Stability AI and Replicate key entry with validation
- [ ] Step 6 supports provider selection (Resend/Brevo/SendGrid) with key entry and configuration
- [ ] Step 6 "Send test email" delivers to current user's email address
- [ ] Step 6 Telegram bot section with test message
- [ ] Step 7 probes Postiz health and shows appropriate UI (setup instructions or platform list)
- [ ] Step 7 supports per-platform integration ID entry
- [ ] All four steps have "Skip for now" that advances without blocking
- [ ] `setup_progress.completed` updates on step completion or skip

---

## Phase 5: MCP Auto-Detect + Review & Launch + Getting Started Banner

**User stories**: US-18, US-19, US-20, US-21

### What to build

The final two wizard steps plus the post-wizard dashboard experience.

**Step 8 — MCP Connections**: a new API endpoint (`GET /api/mcp/detect`) probes known MCP server endpoints in parallel with 2-second timeouts. The wizard page shows three sections: "Auto-detected (running)" with green status, capabilities count, and optional configure button; "Available (not running)" with install/connect instructions; "Add custom MCP server" form for arbitrary URLs. For servers requiring API keys (Figma, Canva, Spotify): inline key entry. Detection covers: Figma, Canva, Supabase, Context7, Desktop Commander, Chrome Extension, Playwright, Spotify, PDF Tools.

**Step 9 — Review & Launch**: categorized summary (Infrastructure, LLM, Brand, Research, Images, Email, Social, MCP). Each item shows configured/missing status with link to the relevant Settings page. Overall readiness percentage. "Launch Dashboard" clears wizard state and redirects to `/`. "Download Config" exports a sanitized `.env.local` (secrets masked, structure preserved).

**Getting Started Banner**: on the dashboard home page, a persistent checklist card that appears for brands with incomplete setup. Items: LLM configured, Brand created, Brand voice configured (voice facts count > 0), First research completed (research items count > 0), First draft generated (drafts count > 0). Progress bar with percentage. Dismissible — sets `setup_progress.dismissed = true`. Does not reappear.

End-to-end demo: Step 8 → Figma MCP detected, Context7 connected → Step 9 → 80% ready, email missing → Launch → dashboard home → Getting Started banner → "Configure email →" link → Settings.

### Acceptance criteria

- [ ] `GET /api/mcp/detect` probes known MCP server endpoints in parallel (≤2s per server)
- [ ] Step 8 shows detected servers with status, capabilities count, and configure actions
- [ ] Step 8 shows available-but-not-running servers with install instructions
- [ ] Step 8 supports custom MCP server URL entry
- [ ] Step 9 shows categorized summary with correct configured/missing status
- [ ] Step 9 readiness percentage calculates correctly based on completed steps
- [ ] Step 9 "Launch Dashboard" clears wizard state, redirects to `/`
- [ ] Getting Started banner appears on dashboard home for brands with incomplete setup
- [ ] Banner items reflect real data (brand exists, voice facts > 0, research items > 0, drafts > 0)
- [ ] Banner dismiss persists via `setup_progress.dismissed = true`
- [ ] Banner does not reappear after dismissal

---

## Phase 6: CLI Operations — providers, brand, start, mcp, status

**User stories**: US-06, US-07, US-08, US-10

### What to build

CLI commands that operate on a running ZeroHuman instance. These require the backend to be running and (for brand-scoped commands) a valid auth session.

**`zh providers list`**: reads provider catalog, checks `.env.local` for env-level keys, calls `/api/llm/providers/configured` for BYOK status. Displays categorized table with configured/not-configured badges.

**`zh providers add <provider-id>`**: interactive prompt for API key, validates prefix, tests via backend `/api/llm/providers/{id}/validate`. On success: asks whether to save to `.env.local` (system-level) or BYOK (brand-level via backend API). Shows latency and available models.

**`zh providers test <provider-id>`**: tests an existing configured provider via backend validation endpoint. Reports latency and model list.

**`zh brand create`**: interactive prompt for name, slug, topics, budget. Creates via backend API (`POST /api/brands`). Sets active brand context for subsequent commands.

**`zh brand list`**: lists all brands for the authenticated user via backend API.

**`zh start`**: starts Next.js + Python backend concurrently (using `concurrently` or `child_process`). Waits for health checks to pass. Reports status. Supports `--docker` flag for Docker Compose mode.

**`zh mcp list`**: shows known MCP servers with connection status (probes endpoints).

**`zh status`**: combined branded output — logo + environment + config summary + provider status + brand list + gateway status + MCP status.

End-to-end demo: `zh providers add openai` → paste key → validated 312ms → saved to `.env.local` → `zh status` → full system overview.

### Acceptance criteria

- [ ] `zh providers list` shows catalog with configured/not-configured status
- [ ] `zh providers add` validates key prefix and tests via backend, offers env vs BYOK save
- [ ] `zh providers test` tests a configured provider and reports latency + models
- [ ] `zh brand create` creates a brand interactively via backend API
- [ ] `zh brand list` lists brands with IDs and slugs
- [ ] `zh start` launches services concurrently with health check verification
- [ ] `zh start --docker` uses Docker Compose
- [ ] `zh mcp list` shows MCP servers with connection status
- [ ] `zh status` displays branded overview combining all system information

---

## Phase 7: CLI Utility Commands + Polish

**User stories**: US-09

### What to build

Remaining utility commands and overall CLI polish for production readiness.

**`zh config get <key>`**: reads a single value from `.env.local` (masked if secret-like).
**`zh config set <key> <value>`**: writes a value to `.env.local` atomically.
**`zh config list`**: displays all config values (secrets auto-masked).
**`zh config path`**: prints the resolved path to `.env.local`.

**`zh migrate`**: runs pending Supabase migrations. If Supabase CLI is available, uses `supabase db push`. Otherwise, reads `.sql` migration files and executes via Supabase REST API. Reports applied count.
**`zh migrate status`**: shows applied vs pending migration count.

**`zh seed`**: runs the agent system seed script (agent_configs, agent_skills, anti-hype examples). Idempotent.
**`zh seed --force`**: re-seeds even if data exists.

**`zh update`**: `git pull origin main` → `npm install` → `cd cli && npm run build` → `cd python && uv sync` → `zh migrate` → reports what changed.
**`zh update --check`**: checks for updates without applying.

**`zh reset`**: removes `.env.local` with confirmation prompt. `zh reset --hard`: also drops all tables and re-creates them (requires explicit "type RESET to confirm").

**Polish**: `--help` text for every command and subcommand. `--version` flag. Consistent colored output (green for success, red for errors, yellow for warnings, cyan for info). Clear error messages with suggested fixes. Graceful handling of missing `.env.local`, unreachable backend, and network errors.

End-to-end demo: `zh update` → pulls latest → installs deps → migrates → "3 new migrations applied, system up to date". `zh config list` → all values displayed, secrets masked.

### Acceptance criteria

- [ ] `zh config get/set/list/path` read and write `.env.local` correctly with secret masking
- [ ] `zh migrate` runs pending migrations and reports count
- [ ] `zh migrate status` shows applied vs pending
- [ ] `zh seed` is idempotent; `zh seed --force` re-creates data
- [ ] `zh update` pulls, installs, builds, syncs, and migrates in sequence
- [ ] `zh update --check` reports available updates without applying
- [ ] `zh reset` removes config with confirmation; `zh reset --hard` drops tables with explicit confirmation
- [ ] Every command has `--help` text
- [ ] `zh --version` prints current version
- [ ] Error messages are clear and suggest specific fixes
- [ ] Missing `.env.local` and unreachable backend are handled gracefully (no stack traces)
