# PRD — Universal Setup Wizard (CLI + Dashboard + Bootstrap)

> Status: Draft 2026-05-19
> Owner: Davide Silvestri
> Supersedes: `setup.sh` (bash script), existing 6-step dashboard wizard
> Related: `plans/fast-setup.md`, `plans/cli-mcp-multi-brand.md`, `docs/plans/2026-05-18-llm-provider-hub-prd.md`

---

## 1. Problem

ZeroHuman Agency today has a **fatal bootstrap problem**: without Supabase credentials in `.env.local`, the app shows a white screen. The middleware (`src/proxy.ts`) crashes on the first request because `NEXT_PUBLIC_SUPABASE_URL!` is undefined. The Python backend won't even start — Pydantic validation fails on the missing required field.

This means:

1. **New users see nothing** — clone the repo, `npm run dev`, white screen, no guidance
2. **The setup wizard is unreachable** — it lives inside `(dashboard)` layout which requires Supabase auth
3. **`setup.sh` is fragile** — bash-only, no Windows support, no interactive validation, no health checks
4. **The wizard is incomplete** — only 6 steps covering LLM + Brand + Voice + Research. Missing: MCP, email, images, social, storage, software detection
5. **No CLI tool exists** — users can't manage configuration, run diagnostics, or automate setup from the terminal
6. **No progress tracking** — if the user closes the wizard mid-way, there's no persistent completion state beyond localStorage

## 2. Target audience

| Persona | Need |
|---------|------|
| **Developer (self-hosted)** | `zh init` → running stack in 5 minutes, no docs needed |
| **Semi-technical user** | Dashboard wizard guides through every integration visually |
| **CI/CD pipeline** | `zh init --non-interactive` with all flags for automated deployment |
| **Existing user upgrading** | `zh doctor` to diagnose issues, wizard re-entry for new integrations |
| **Team onboarding** | Share a pre-configured `.env.local` or run wizard to add brand-specific keys |

## 3. Goals

1. **Zero white screen** — the app always boots. Missing Supabase → bootstrap page. Missing setup → wizard.
2. **`zh` CLI** — a proper Node.js CLI tool replacing `setup.sh` with interactive prompts, health checks, provider management, and branded output with the Verified Knot logo.
3. **Comprehensive wizard** — 10 steps covering every integration (LLM providers, brand, voice, research, images, email, social, MCP, review) with skip-for-now on optionals.
4. **MCP auto-detect** — scan connected MCP servers, show which are available, configure API keys for each.
5. **Two-layer architecture** — CLI handles infrastructure (Supabase, env vars, migrations); dashboard handles user-facing config (providers, brand, integrations).
6. **Logo everywhere** — Verified Knot ASCII art in CLI, SVG in dashboard bootstrap and wizard.

## 4. Non-goals

- SQLite fallback (no dual-database support)
- Full in-browser Supabase project creation (too complex, edge cases)
- Go/Rust binary for CLI (Node.js is already required)
- Replacing the Settings pages (wizard complements them, doesn't replace)

---

## 5. Architecture

### 5.1 Boot flow

```
User navigates to app
         |
    middleware.ts
         |
    SUPABASE_URL set?
    /            \
  NO              YES
   |               |
/bootstrap      normal auth
(static page,   /         \
 no auth,     /login     /dashboard
 no DB)         |           |
              auth ok?    setup complete?
              /    \      /           \
            NO    YES   NO            YES
            |      |    |              |
          /login  ...  /setup        /dashboard
                       (wizard)
```

### 5.2 Route groups

| Route group | Auth required | Supabase required | Purpose |
|-------------|---------------|-------------------|---------|
| `(bootstrap)` | No | No | Pre-Supabase: instructions + manual credential form |
| `(auth)` | No | Yes | Login/signup |
| `(dashboard)` | Yes | Yes | Main app + setup wizard |

### 5.3 CLI architecture

```
cli/
  package.json          # @zerohuman/cli, bin: { zh: "./dist/index.js" }
  src/
    index.ts            # Entry point, command router
    commands/
      init.ts           # Full interactive setup
      start.ts          # Start all services
      doctor.ts         # Diagnose dependencies + connections
      config.ts         # Get/set config values
      migrate.ts        # Run Supabase migrations
      seed.ts           # Seed agent system
      providers.ts      # List/add/test/remove LLM providers
      brand.ts          # Create/list brands
      mcp.ts            # List/add MCP servers
      status.ts         # Full system health report
      update.ts         # Update ZeroHuman
      reset.ts          # Factory reset
    lib/
      logo.ts           # ASCII Verified Knot art
      env-writer.ts     # Read/write .env.local safely
      health.ts         # Health check utilities
      prompts.ts        # Shared prompt helpers
      supabase.ts       # Supabase client for CLI context
```

**Runtime:** Node.js (already required for Next.js)
**Libraries:** `@clack/prompts` (interactive prompts), `chalk` (colors), `ora` (spinners), `commander` (command parsing), `dotenv` (env reading)
**Installation:** `npx @zerohuman/cli init` or global `npm i -g @zerohuman/cli` then `zh init`

### 5.4 Verified Knot in CLI

The CLI displays the Verified Knot logo as ASCII art on `zh init` and `zh status`. The logo follows the brand philosophy: obsidian on dark terminals, ivory on light. Coral (`#FF6B6B`) used only for the verification indicator (checkmarks, success states).

```
    ╭──────────────────────────────────╮
    │                                  │
    │    ⣿⣿⡆  ⢰⣿⣿    ZeroHuman      │
    │    ⣿⣿⣿⣄⣠⣿⣿⣿    Agency         │
    │    ⣿⣿ ⣿⣿⣿ ⣿⣿                   │
    │    ⣿⣿  ⣿⣿  ⣿⣿    v1.0.0        │
    │    ⣿⣿  ⠀⠀  ⣿⣿                   │
    │                                  │
    ╰──────────────────────────────────╯
```

_(actual glyph to be refined with the real SVG → Braille block conversion)_

---

## 6. `zh` CLI — Command specification

### 6.1 `zh init`

Full interactive setup from zero to running stack. Replaces `setup.sh`.

**Flow:**

```
Step 1: Environment Check
  - Detect OS, Node version, Python version, Docker availability
  - Detect package manager (npm/pnpm/yarn/bun)
  - Check for uv (Python package manager)
  - Report: what's installed, what's missing, what's recommended
  - Auto-install suggestions (e.g., "brew install uv")

Step 2: Supabase Setup
  - Three paths:
    a) "I have a Supabase Cloud project" → prompt URL + anon key + service role key
    b) "I want to self-host with Docker" → check Docker, pull supabase images, start
    c) "I already have credentials in .env.local" → validate existing
  - Test connection: call /rest/v1/ with anon key
  - If connection fails: clear error message with troubleshooting hints

Step 3: LLM Provider (at least 1 required)
  - Show categorized provider list from PROVIDER_CATALOG
  - User selects providers to configure (multi-select)
  - For each selected: prompt API key, validate prefix, test key via /models endpoint
  - Show latency + available models on success
  - At least one must succeed to proceed

Step 4: Encryption Keys (auto-generated)
  - Generate BRAND_SECRETS_ENCRYPTION_KEY (Fernet)
  - Generate SCHEDULER_SECRET (hex 32)
  - Display with copy-to-clipboard hint

Step 5: Optional Services (skip-friendly)
  - Research: Serper, Tavily, YouTube API keys
  - Email: Resend or Brevo API key + from address
  - Images: OpenAI (DALL-E), Stability AI, Replicate token
  - Social: Postiz mode + URL + API key
  - Alerts: Telegram bot token + chat ID
  - Each shows "Skip" as default, "Add" to configure

Step 6: Write Configuration
  - Preview all values (secrets masked)
  - Write .env.local atomically (write to .env.local.tmp, rename)
  - If .env.local exists: diff + confirm overwrite or merge

Step 7: Database Setup
  - Run Supabase migrations (supabase db push or direct SQL via API)
  - Seed agent system (agent_configs, agent_skills, anti-hype examples)
  - Verify tables exist

Step 8: Health Check
  - Test all configured services in parallel
  - Display results table: service, status, latency
  - Overall readiness score
  - "Run zh start to launch" or "Run npm run dev"
```

**Non-interactive mode:**

```bash
zh init \
  --supabase-url=https://xxx.supabase.co \
  --supabase-anon-key=eyJ... \
  --supabase-service-key=eyJ... \
  --anthropic-key=sk-ant-... \
  --openai-key=sk-... \
  --serper-key=... \
  --no-docker \
  --no-migrations \
  --yes  # accept all defaults
```

### 6.2 `zh doctor`

Diagnostic tool. Checks everything and reports issues.

```
$ zh doctor

  ZeroHuman Doctor
  ────────────────────────────

  Environment
  ├ Node.js       22.3.0     ✓
  ├ Python        3.12.4     ✓
  ├ uv            0.7.2      ✓
  ├ Docker        27.3.1     ✓ (optional)
  └ Supabase CLI  2.11.0     ✓ (optional)

  Configuration (.env.local)
  ├ SUPABASE_URL             ✓ https://xxx.supabase.co
  ├ SUPABASE_ANON_KEY        ✓ eyJ...abc
  ├ SUPABASE_SERVICE_KEY     ✓ eyJ...xyz
  ├ ANTHROPIC_API_KEY        ✓ sk-ant-...abc
  ├ OPENAI_API_KEY           ✗ not set
  ├ SERPER_API_KEY           ✓ set
  └ ENCRYPTION_KEY           ✓ set

  Connections
  ├ Supabase DB              ✓ 23ms
  ├ Supabase Auth            ✓ 45ms
  ├ Python Backend           ✓ 12ms (port 8082)
  ├ Anthropic API            ✓ 312ms
  └ Serper API               ✓ 89ms

  Database
  ├ Migrations               ✓ 43/43 applied
  ├ Agent configs            ✓ 4 agents
  └ Agent skills             ✓ 12 skills

  Local Gateways
  ├ Ollama (11434)           ✗ not running
  ├ LM Studio (1234)         ✗ not running
  └ OpenClaw (18789)         ✗ not running

  Overall: ✓ Ready (2 optional services not configured)
```

### 6.3 `zh providers`

```
zh providers list                  # Show all catalog providers + configured status
zh providers add <provider-id>     # Interactive: prompt key, validate, save to .env.local
zh providers test <provider-id>    # Test existing key (latency + models)
zh providers remove <provider-id>  # Remove key from .env.local
```

### 6.4 `zh start`

```
zh start              # Start Next.js + Python backend (concurrent)
zh start --docker     # Start via docker-compose.full.yaml
zh start --api-only   # Start only the Python backend
zh start --web-only   # Start only the Next.js frontend
```

### 6.5 `zh brand`

```
zh brand create           # Interactive: name, slug, topics, budget
zh brand list             # List all brands (requires running backend + auth)
zh brand switch <slug>    # Set active brand for CLI operations
```

### 6.6 `zh mcp`

```
zh mcp list               # Show available MCP servers + connection status
zh mcp add <server-id>    # Configure an MCP server interactively
zh mcp test <server-id>   # Test MCP server connection
```

### 6.7 `zh config`

```
zh config get <key>           # Read a value from .env.local
zh config set <key> <value>   # Write a value to .env.local
zh config list                # Show all config (secrets masked)
zh config path                # Print path to .env.local
```

### 6.8 `zh migrate`

```
zh migrate                # Run all pending Supabase migrations
zh migrate status         # Show migration status (applied vs pending)
zh migrate create <name>  # Create a new migration file
```

### 6.9 `zh seed`

```
zh seed                   # Seed agent configs, skills, anti-hype examples
zh seed --force           # Re-seed even if data exists
```

### 6.10 `zh status`

```
zh status                 # Full system overview (logo + health + config summary)
```

### 6.11 `zh update`

```
zh update                 # git pull + npm install + uv sync + migrate
zh update --check         # Check if updates are available without applying
```

### 6.12 `zh reset`

```
zh reset                  # Remove .env.local, clear localStorage prompt
zh reset --hard           # Also drop all tables and re-migrate (DANGEROUS)
```

---

## 7. Dashboard Wizard — Step specification

The dashboard wizard replaces the existing 6-step wizard with a comprehensive 10-step flow. It lives at `/setup` within the `(dashboard)` route group (requires auth).

### 7.0 Step: Infrastructure Check

**Purpose:** Verify the backend is healthy before proceeding.

**Behavior:**
- Auto-runs health checks: Supabase connection, Python backend reachability, migration status
- Shows green/red status for each
- If Python backend is unreachable: show "Start the backend with `zh start` or `npm run dev:api`"
- If migrations pending: show "Run `zh migrate` in your terminal"
- Auto-proceeds if all checks pass

**Required:** Yes (blocks if critical failures)

### 7.1 Step: LLM Providers

**Purpose:** Configure at least one LLM provider.

**Behavior:**
- Shows ALL 22+ providers from `PROVIDER_CATALOG`, grouped by category:
  - **Priority providers (P0)**: Anthropic, OpenAI, Google AI, Groq — always visible
  - **More providers (P1/P2)**: collapsible section
  - **Local gateways**: Ollama, LM Studio, vLLM, LiteLLM, OpenClaw — with auto-discover button
  - **Meta-routers**: OpenRouter
- Each provider: expand to enter key, validate, save (existing `InlineKeyEntry` pattern)
- Shows which are already configured via BYOK or env var
- **Can add multiple providers** — the wizard encourages adding 2+ for fallback
- Gateway auto-discover: probes localhost ports, shows online gateways with model counts

**Required:** At least 1 provider must be configured (BYOK or env var)

### 7.2 Step: Brand Identity

**Purpose:** Create the first brand.

**Behavior:**
- If a brand already exists: show it, allow editing, or "Create another"
- Fields: Brand name, slug (auto-generated), description (new), website URL (new), topics (tag input)
- Logo upload (drag-and-drop or file picker) — saved to brand_assets
- Primary color picker — saved to brand_assets as palette
- Daily budget (USD) — optional

**Required:** Yes (at least one brand must exist)

### 7.3 Step: Brand Voice

**Purpose:** Establish brand voice rules.

**Behavior:**
- Three paths (tabs):
  - **Auto-Discover**: paste website URLs → AI extracts tone rules, principles, examples
  - **Template**: pick from sector templates (SaaS, e-commerce, fitness, etc.)
  - **Manual**: skip and configure later in Settings
- Review extracted/template facts with edit + include/exclude toggles
- Save to `memory_semantic` via existing API

**Required:** No (skipable with "Skip for now")

### 7.4 Step: Research Tools

**Purpose:** Configure research API keys for content discovery.

**Behavior:**
- Show current tier: Free (DuckDuckGo + RSS) / Tavily / Premium (Serper + YouTube)
- For each research service: inline key entry (same pattern as LLM)
  - Serper: `SERPER_API_KEY`
  - Tavily: `TAVILY_API_KEY` (note: 1000 free searches/month)
  - YouTube Data API: `YOUTUBE_API_KEY`
- Show what each tier unlocks
- Tier upgrades automatically as keys are added

**Required:** No (Free tier works out of the box)

### 7.5 Step: Image Generation

**Purpose:** Configure image generation backends.

**Behavior:**
- Available backends:
  - OpenAI DALL-E 3 (uses OPENAI_API_KEY — auto-detected if already set in Step 1)
  - Stability AI: key entry + test
  - Replicate: token entry + test
- Show which are available based on already-configured keys
- Preview: test generation with a simple prompt

**Required:** No (skipable)

### 7.6 Step: Email & Notifications

**Purpose:** Configure email delivery and alert channels.

**Behavior:**
- Email providers (pick one):
  - Resend: API key + from address + test email
  - Brevo: API key + from address + test email
  - SendGrid: API key + from address + test email
- Notification channels:
  - Telegram: bot token + chat ID + test message
  - Webhook URL: custom endpoint for alerts
- From name + from email configuration

**Required:** No (skipable — email features disabled)

### 7.7 Step: Social Publishing

**Purpose:** Connect social media platforms via Postiz.

**Behavior:**
- Check Postiz status: is it running? (probe API)
- If not running: instructions to set up Postiz (Docker or cloud)
- If running: show platform list (LinkedIn, X, Instagram, TikTok, YouTube, Threads, etc.)
- For each platform: paste Postiz Integration ID (manual OAuth through Postiz UI)
- Test each connection

**Required:** No (skipable — social publishing disabled)

### 7.8 Step: MCP Connections

**Purpose:** Configure MCP (Model Context Protocol) servers for extended capabilities.

**Behavior:**
- **Auto-detect phase**: scan for running MCP servers by probing known endpoints
  - Figma MCP: check if connected
  - Canva MCP: check if connected
  - Supabase MCP: check if connected
  - Context7 MCP: check URL reachability
  - Desktop Commander MCP: check if running
  - Chrome MCP: check if extension connected
  - Custom MCP servers: user can add URL
- For each detected server: show status (connected/disconnected), capabilities, configure action
- For servers requiring API keys: inline key entry
- For servers requiring software: download/install instructions + detection
- MCP server catalog: show all supported servers with install buttons

**Auto-detect logic:**
```
For each known MCP server:
  1. Check if the MCP server process is running (port probe or process check)
  2. If running: fetch capabilities list
  3. Show: server name, status, capabilities count, configure button
  4. If not running: show "Install" button with instructions
```

**Required:** No (skipable — MCP features work with defaults)

### 7.9 Step: Review & Launch

**Purpose:** Summary of everything configured, final health check, launch.

**Behavior:**
- Full checklist organized by category:
  - Infrastructure: Supabase ✓, Backend ✓, Migrations ✓
  - LLM: list configured providers with latency
  - Brand: name, voice facts count, logo status
  - Research: tier + configured APIs
  - Images: configured backends
  - Email: configured provider + from address
  - Social: connected platforms count
  - MCP: connected servers count
- Missing items shown with "Configure →" links to specific settings pages
- Overall readiness score (percentage)
- "Launch Dashboard" button → clears wizard state, redirects to `/`
- "Download Config" button → exports .env.local as file (for backup/sharing)

**Required:** Yes (terminal step)

---

## 8. Bootstrap Page (`/bootstrap`)

The bootstrap page is shown when Supabase is not configured. It exists outside the `(dashboard)` layout group and requires NO database, NO auth.

### 8.1 Middleware changes

```typescript
// src/lib/supabase/middleware.ts
export async function updateSession(request: NextRequest) {
  // NEW: If Supabase is not configured, redirect to /bootstrap
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  
  if (!supabaseUrl || !supabaseKey) {
    // Allow /bootstrap and its assets
    if (request.nextUrl.pathname.startsWith('/bootstrap') ||
        request.nextUrl.pathname.startsWith('/_next') ||
        request.nextUrl.pathname.startsWith('/api/bootstrap')) {
      return NextResponse.next({ request })
    }
    const url = request.nextUrl.clone()
    url.pathname = '/bootstrap'
    return NextResponse.redirect(url)
  }

  // ... existing auth flow
}
```

### 8.2 Bootstrap page content

Static page with:

1. **ZeroHuman logo** (SVG, Verified Knot)
2. **Welcome message**: "ZeroHuman Agency needs a database to get started."
3. **Option A — CLI (recommended)**:
   ```
   Install the CLI and run the setup wizard:
   
   npx @zerohuman/cli init
   ```
   With copy button.

4. **Option B — Manual configuration**:
   Collapsible section with:
   - Supabase URL input
   - Supabase Anon Key input
   - Supabase Service Role Key input
   - "Test Connection" button (calls `/api/bootstrap/test-connection`)
   - "Save & Restart" button (writes to `.env.local` via `/api/bootstrap/save-config`)

5. **Option C — Documentation link**:
   Link to `docs/SETUP.md` for full manual setup.

### 8.3 Bootstrap API endpoints

These endpoints exist outside the auth middleware and do NOT require Supabase:

```
POST /api/bootstrap/test-connection
  Body: { supabase_url, supabase_anon_key, supabase_service_key }
  Action: attempt to connect to Supabase, verify tables exist
  Returns: { success, error?, tables_found? }

POST /api/bootstrap/save-config
  Body: { supabase_url, supabase_anon_key, supabase_service_key }
  Action: write values to .env.local, signal process restart
  Returns: { success, restart_required: true }
```

**Security:** These endpoints only function when Supabase is NOT already configured. Once `.env.local` has Supabase credentials, these endpoints return 403.

---

## 9. MCP Auto-Detect Specification

### 9.1 Known MCP servers

| Server | Detection method | Config needed |
|--------|-----------------|---------------|
| Figma MCP | Check `mcp__Figma__*` tool availability | Figma token |
| Canva MCP | Check `mcp__84135c75__*` tool availability | Canva token |
| Supabase MCP | Check `mcp__36ebf3d3__*` tool availability | Project ref (auto from env) |
| Context7 | HTTP probe to `context7_mcp_url` | URL (has default) |
| Desktop Commander | Check `mcp__Desktop_Commander__*` availability | None (local) |
| Chrome Extension | Check `mcp__Claude_in_Chrome__*` availability | None (extension) |
| Playwright | Check `mcp__plugin_playwright__*` availability | None (local) |
| Spotify | Check `mcp__73092f78__*` availability | Spotify OAuth |
| PDF Tools | Check `mcp__5419628b__*` availability | None (local) |

### 9.2 Dashboard MCP step UI

```
┌─────────────────────────────────────────────┐
│  MCP Connections                            │
│                                             │
│  Auto-detected (running):                   │
│  ┌──────────────────────────────────┐       │
│  │ ✓ Figma MCP         Connected   │       │
│  │   12 tools available  [Config]  │       │
│  ├──────────────────────────────────┤       │
│  │ ✓ Desktop Commander  Connected   │       │
│  │   28 tools available            │       │
│  ├──────────────────────────────────┤       │
│  │ ✓ Context7           Connected   │       │
│  │   2 tools available             │       │
│  └──────────────────────────────────┘       │
│                                             │
│  Available (not running):                   │
│  ┌──────────────────────────────────┐       │
│  │ ○ Canva MCP          [Install]  │       │
│  │ ○ Playwright          [Install] │       │
│  │ ○ Spotify MCP         [Install] │       │
│  └──────────────────────────────────┘       │
│                                             │
│  [+ Add custom MCP server]                  │
│                                             │
│  [Skip for now]              [Continue →]   │
└─────────────────────────────────────────────┘
```

---

## 10. Setup progress persistence

### 10.1 Database schema

```sql
-- New: setup_progress table
CREATE TABLE IF NOT EXISTS public.setup_progress (
  brand_id      uuid PRIMARY KEY REFERENCES public.brands(id) ON DELETE CASCADE,
  completed     jsonb NOT NULL DEFAULT '{}'::jsonb,
  -- e.g. {"infrastructure": true, "llm": true, "brand": true, "voice": false, ...}
  wizard_state  jsonb DEFAULT '{}'::jsonb,
  -- transient wizard state (current step, partial form data)
  dismissed     boolean NOT NULL DEFAULT false,
  -- user dismissed the "Getting Started" banner
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.setup_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY setup_progress_brand ON public.setup_progress
  USING (public.user_has_brand(brand_id))
  WITH CHECK (public.user_has_brand(brand_id));
```

### 10.2 Getting Started banner

After wizard completion (or skip), the dashboard home shows a "Getting Started" checklist banner:

```
┌─────────────────────────────────────────────────────┐
│  Getting Started                          [Dismiss] │
│                                                     │
│  ✓ LLM provider configured (Anthropic + Groq)      │
│  ✓ Brand created (Acme Corp)                        │
│  ○ Brand voice not configured    [Set up →]         │
│  ✓ First research completed                         │
│  ○ First draft not generated     [Create →]         │
│                                                     │
│  ████████████░░░░  60% complete                     │
└─────────────────────────────────────────────────────┘
```

---

## 11. User stories

### Infrastructure & Bootstrap
- **US-01**: As a new user, I clone the repo and see a helpful bootstrap page instead of a white screen.
- **US-02**: As a developer, I run `zh init` and have a fully configured stack in under 5 minutes.
- **US-03**: As a CI pipeline, I run `zh init --non-interactive` with all flags to deploy automatically.
- **US-04**: As a user, I can enter Supabase credentials on the bootstrap page without using the CLI.

### CLI
- **US-05**: As a developer, I run `zh doctor` and immediately see what's broken and how to fix it.
- **US-06**: As a developer, I run `zh providers add openai` and configure a new provider without editing files.
- **US-07**: As a developer, I run `zh status` and see a branded overview of my entire system.
- **US-08**: As a developer, I run `zh start` and all services launch with health checks.
- **US-09**: As a developer, I run `zh update` and the system updates, migrates, and restarts.
- **US-10**: As a developer, I run `zh mcp list` and see which MCP servers are available.

### Dashboard Wizard
- **US-11**: As a user, I complete the wizard and have at least 1 LLM provider + 1 brand configured.
- **US-12**: As a user, I can configure multiple LLM providers for fallback resilience.
- **US-13**: As a user, I skip optional steps and complete them later from Settings.
- **US-14**: As a user, I close the wizard mid-way and resume from where I left off.
- **US-15**: As a user, I see auto-discovered local gateways (Ollama, LM Studio) in the LLM step.
- **US-16**: As a user, I configure image generation backends (DALL-E, Stability, Replicate).
- **US-17**: As a user, I configure email delivery with a test email before proceeding.
- **US-18**: As a user, I see which MCP servers are connected and can configure new ones.
- **US-19**: As a user, the Review step shows me a complete picture of what's configured and what's missing.

### Progress & Re-entry
- **US-20**: As a user, I see a "Getting Started" banner on the dashboard with completion progress.
- **US-21**: As a user, I dismiss the Getting Started banner and it doesn't come back.
- **US-22**: As a user, I can re-enter the wizard from Settings to configure additional integrations.

---

## 12. Technical constraints

1. **The bootstrap page must work with ZERO JavaScript frameworks** if possible — or at minimum with zero Supabase calls. It can use React but must not import any Supabase client.
2. **The CLI must work on macOS, Linux, and Windows** (WSL acceptable for Windows).
3. **The CLI writes `.env.local` atomically** — write to temp file, then rename.
4. **The bootstrap API endpoints (`/api/bootstrap/*`) are disabled once Supabase is configured** — this prevents credential overwrite attacks.
5. **The wizard persists progress server-side** (in `setup_progress` table), not just localStorage — so it survives browser clears and works across devices.
6. **MCP auto-detect must be fast** — probe in parallel with 2-second timeout per server.
7. **All secrets entered in the wizard are encrypted** via the existing brand_secrets Fernet vault — never stored in plaintext in the database.

---

## 13. Open questions

1. **Should `zh init` create the first Supabase user (signup)?** Currently auth requires going to the dashboard login page. Could `zh init` also create the first admin user via Supabase Admin API?
2. **Should the bootstrap page support OAuth providers** (Google, GitHub) for the initial Supabase auth setup, or just email/password?
3. **Should `zh` be published to npm as `@zerohuman/cli` or bundled in the monorepo?** Publishing to npm enables `npx @zerohuman/cli init` without cloning. Bundling keeps it simpler.
4. **Should the wizard support "profiles"** — e.g., "Minimal (LLM + Brand)", "Content Creator (+ Research + Images)", "Full Agency (everything)" — as a meta-step that pre-selects which steps to show?
