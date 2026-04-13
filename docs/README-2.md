# Content Engine — Open Source AI Automation Framework

> **Build once. Adapt forever.**
> An AI-powered content automation framework you can plug into any business, brand, or content vertical in hours — not weeks.

---

## What Is This?

Content Engine is an **open-source, vertical-agnostic framework** for autonomous AI-driven content operations. It handles research, scoring, writing, reviewing, and publishing — continuously, without manual intervention — and can be adapted to any domain: media companies, B2B SaaS, e-commerce, industrial companies, personal brands, newsletters, or any organization that needs to stay informed and produce content at scale.

The project was born from a real experiment: replicating and systematizing the "AI Media Company" model explored by content creators and thought leaders over 14 days, then abstracting it into a repeatable, configurable engine that anyone can deploy.

**What it is NOT:**
- A chatbot or conversational AI
- A no-code tool with a visual interface
- A single-brand application (it's a framework — your brand is the config, not the code)

---

## Core Philosophy

```
Research → Score → Write → Review → Publish → Learn → Repeat
```

Every step is automated. Every step is auditable. Every step is configurable per vertical. The core engine never changes — only your vertical configuration does.

This is the "empty box" principle: the same machine powers a sponsorship intelligence platform, a wooden pallet industry newsletter, and a tech media company. The pipeline stays identical; the topic, tone, sources, scoring criteria, and output format are vertical-specific.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CONTENT ENGINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      CORE (FIXED)                       │   │
│  │  Orchestrator · Scheduler · State Machine · Logging     │   │
│  │  Audit Trail · Rate Limiting · Retry Logic · DB Schema  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│         ┌────────────────────┼────────────────────┐            │
│         ▼                    ▼                    ▼            │
│  ┌─────────────┐    ┌─────────────────┐  ┌──────────────┐     │
│  │   AGENTS    │    │    ADAPTERS     │  │   VERTICAL   │     │
│  │  (Runtime)  │    │  (Integrations) │  │   CONFIGS    │     │
│  │             │    │                 │  │              │     │
│  │ • Research  │    │ • RSS/Feeds     │  │ /media/      │     │
│  │ • Scoring   │    │ • Web Search    │  │ /b2b/        │     │
│  │ • Writer    │    │ • YouTube       │  │ /industrial/ │     │
│  │ • Editor    │    │ • LinkedIn      │  │ /custom/     │     │
│  │ • GOD Mode  │    │ • Newsletter    │  │              │     │
│  └─────────────┘    │ • Embeddings    │  └──────────────┘     │
│                     └─────────────────┘                        │
│                              │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     OUTPUTS                             │   │
│  │  Newsletter · LinkedIn · Blog · Report · Alert · Feed   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
content-engine/
│
├── python/                          # Core backend (Python / FastAPI)
│   ├── src/
│   │   └── content_engine/
│   │       ├── core/
│   │       │   ├── orchestrator.py      # Main pipeline coordinator
│   │       │   ├── scheduler.py         # Job scheduling and triggers
│   │       │   ├── state_machine.py     # Pipeline state management
│   │       │   └── observability.py     # Logging, metrics, health checks
│   │       │
│   │       ├── agents/
│   │       │   ├── research.py          # Research agent: collects raw items
│   │       │   ├── scoring_engine.py    # Scoring agent: 0-100 relevance
│   │       │   ├── writer.py            # Writer agent: content generation
│   │       │   ├── editor.py            # Editor agent: quality review
│   │       │   └── god_system.py        # GOD Mode: multi-agent review panel
│   │       │
│   │       ├── retrievers/
│   │       │   ├── rss.py               # RSS / Atom feed parser
│   │       │   ├── serper.py            # Google/Bing web search via Serper
│   │       │   ├── youtube.py           # YouTube Data API v3
│   │       │   ├── firecrawl.py         # Full-page scraper
│   │       │   └── newsletter.py        # Email newsletter digest parser
│   │       │
│   │       ├── outputs/
│   │       │   ├── newsletter_delivery.py  # Resend ESP integration
│   │       │   ├── social_publisher.py     # LinkedIn UGC Post API
│   │       │   ├── blog_writer.py          # Markdown/HTML blog output
│   │       │   └── report_generator.py     # Structured PDF/MD reports
│   │       │
│   │       ├── memory/
│   │       │   ├── feedback_loop.py     # Engagement → scoring feedback
│   │       │   ├── deduplication.py     # URL + semantic dedup (pgvector)
│   │       │   └── long_term.py         # Published item history
│   │       │
│   │       └── verticals/               # ← YOUR BRAND LIVES HERE
│   │           ├── _template/           # Copy this to create your vertical
│   │           │   ├── config.yaml
│   │           │   ├── scoring_rubric.yaml
│   │           │   ├── prompts/
│   │           │   └── sources.yaml
│   │           ├── media_company/       # Example: tech media brand
│   │           ├── b2b_saas/            # Example: SaaS newsletter
│   │           └── industrial/          # Example: B2B industrial intel
│   │
│   ├── main.py                          # FastAPI app entry point
│   ├── settings.py                      # Environment configuration
│   └── requirements.txt
│
├── src/                             # Frontend (Next.js / TypeScript)
│   └── app/
│       └── dashboard/               # Monitoring dashboard
│           ├── page.tsx             # Overview: pipeline status, KPIs
│           ├── ricerca/             # Research items queue
│           ├── scoring/             # Score distribution, approval
│           ├── content-hub/         # Content by platform
│           ├── newsletter/          # Newsletter management
│           ├── metriche/            # Analytics and feedback
│           ├── costi-api/           # Real-time API cost tracking
│           ├── writing-lab/         # Manual A/B testing
│           └── revenue/             # Monetization tracking
│
├── supabase/
│   ├── migrations/                  # Database schema
│   └── seed/                        # Example data for testing
│
├── docs/                            # Extended documentation
│   ├── ARCHITECTURE.md              # Deep-dive architecture guide
│   ├── VERTICAL_GUIDE.md            # How to adapt to your vertical
│   ├── AGENTS.md                    # Agent contracts and behavior
│   ├── SCORING.md                   # Scoring rubric design guide
│   ├── DEPLOYMENT.md                # Deployment options (Railway, Render, VPS)
│   ├── COST_MODEL.md                # API cost estimation and optimization
│   └── examples/
│       ├── media-company.md
│       ├── b2b-intelligence.md
│       └── industrial-newsletter.md
│
├── .env.example                     # All required environment variables
├── docker-compose.yml               # Local development stack
└── README.md                        # This file
```

---

## How the Pipeline Works

A full autonomous cycle — from raw signals to published content — runs daily with zero manual intervention.

```
07:00 AM ──► RESEARCH PHASE
             Research agent queries all configured sources:
             RSS feeds, web search, YouTube, newsletters.
             Each item is stored with URL, title, summary, source type.

             ▼

08:00 AM ──► DEDUPLICATION
             URL-based exact dedup + semantic similarity check (pgvector).
             Items already published (or too similar to published items)
             are filtered out before scoring.

             ▼

08:30 AM ──► SCORING PHASE
             Scoring agent evaluates each item against your rubric:
             Relevance · Novelty · Trend strength · Audience fit · Risk
             Items scored 0–100. Only items above your threshold proceed.

             ▼

10:00 AM ──► WRITING PHASE
             Writer agent generates content for approved items.
             Each item is written in platform-specific formats:
             LinkedIn post · Newsletter section · Blog draft · Report entry.

             ▼

11:00 AM ──► GOD MODE REVIEW (optional, configurable)
             Multi-agent review panel runs on high-stakes content:
             Advocate → FactCheck → Creative → Synthesis
             Each sub-agent adds structured feedback.
             Final content score determines auto-approve or flag for human.

             ▼

12:00 PM ──► PUBLISH PHASE
             Approved content is published to configured channels.
             Each publish event is logged with timestamp, platform, result.

             ▼

CONTINUOUS ► FEEDBACK LOOP
             Engagement metrics flow back into scoring.
             High-performing topics get boosted in future scoring rounds.
             The system improves automatically over time.
```

---

## The Agents

### Research Agent
**Role:** Collect raw intelligence from the world.

**Input:** List of configured sources (RSS URLs, search queries, YouTube channels, newsletters)
**Output:** List of `ResearchItem` objects with title, summary, URL, source type, retrieved timestamp

**Key behavior:**
- Queries all sources in parallel using `asyncio.gather()`
- Falls back gracefully if a source is unavailable
- Respects rate limits per source
- Stores raw items before deduplication

---

### Scoring Agent
**Role:** Decide what's worth turning into content.

**Input:** List of deduplicated `ResearchItem` objects + vertical scoring rubric
**Output:** Scored items with `final_score` (0–100) and score breakdown

**Scoring dimensions (configurable per vertical):**
```yaml
# scoring_rubric.yaml example
dimensions:
  relevance:     weight: 0.35   # How closely does this match our topic?
  novelty:       weight: 0.25   # Is this genuinely new information?
  trend_signal:  weight: 0.20   # Is this topic gaining momentum?
  audience_fit:  weight: 0.15   # Does this serve our specific audience?
  risk:          weight: 0.05   # Reputational, factual, or legal risk?

thresholds:
  auto_approve:  75    # Score >= 75: goes directly to writing
  review_queue:  50    # Score 50-74: flagged for human review
  discard:       49    # Score < 50: archived, not processed
```

**Cost optimization:** Uses a two-stage model. A lightweight model (e.g., Haiku/Flash) pre-filters from 500 to ~150 candidates. A premium model runs only on those 150.

---

### Writer Agent
**Role:** Transform approved items into platform-ready content.

**Input:** Scored and approved `ResearchItem` + vertical tone/style prompts
**Output:** `ContentAsset` with platform-specific variants

**Output variants per item:**
- `linkedin_post`: 150–300 words, professional tone, call to action
- `newsletter_section`: 200–400 words, contextual, linked
- `blog_draft`: 600–1200 words, SEO-friendly, structured
- `report_entry`: 100–200 words, factual, data-forward

---

### Editor Agent
**Role:** Quality gate before publish.

**Input:** Raw content drafts from Writer
**Output:** Edited content with change log and approval status

**Checks performed:**
- Factual consistency with source material
- Tone alignment with vertical config
- Grammar and clarity
- Forbidden phrases / brand safety rules (configurable)
- Duplicate detection against recently published content

---

### GOD Mode (Multi-Agent Review Panel)
**Role:** Deep review for high-stakes or high-score content.

GOD Mode runs a structured panel of sub-agents sequentially:

```
Advocate Agent
└─ Builds the strongest possible case FOR publishing this item.
   Output: advocacy_feedback (text)

      ▼

FactCheck Agent
└─ Challenges every factual claim in the draft.
   Input: original draft + advocacy_feedback
   Output: factcheck_feedback (text)

      ▼

Creative Agent
└─ Suggests improvements to angle, framing, and hook.
   Input: original draft + advocacy_feedback + factcheck_feedback
   Output: creative_feedback (text)

      ▼

Synthesis Agent
└─ Integrates all feedback into a final, improved version.
   Input: all previous outputs
   Output: final_content (text) + god_score (0-100)
```

**When to use GOD Mode:**
- Content that mentions competitors, public figures, or legal topics
- Items with a high initial score (≥ 85) — high stakes
- Configurable: you can disable GOD Mode entirely for low-cost verticals

---

## Adapters (Data Sources)

Each adapter connects the engine to a real-world data source. Adapters are modular: add or remove them per vertical without touching any agent code.

| Adapter | What it does | API Required |
|---------|-------------|-------------|
| `rss.py` | Parses RSS/Atom feeds from any URL | None |
| `serper.py` | Web search via Serper (Google results) | Serper API key |
| `youtube.py` | Searches videos, monitors channels, extracts transcripts | YouTube Data API v3 |
| `firecrawl.py` | Full-page scraping with JavaScript rendering | Firecrawl API key |
| `newsletter.py` | Parses forwarded newsletters or scraped digests | None |

**Why YouTube?**
YouTube is one of the earliest trend signals available. Creators publish video content 2–3 weeks before the same topics appear in blog posts, newsletters, or LinkedIn. A video with 100K+ views on a topic is a leading indicator of what your audience will be reading about next month. The YouTube adapter extracts this signal and feeds it into scoring as a `trend_boost` multiplier.

---

## Database Schema (Supabase / PostgreSQL)

```sql
-- Core tables (simplified)

research_items          -- Raw items collected by Research agent
  id, vertical_id, title, url, summary, source_type,
  retrieved_at, dedup_hash, embedding (vector)

scored_items            -- Items that passed scoring
  id, research_item_id, final_score, score_breakdown (jsonb),
  status (pending|approved|rejected|review), scored_at

content_assets          -- Generated content, all platform variants
  id, scored_item_id, platform, content (text),
  god_score, status, created_at

publish_log             -- Immutable audit trail of every publish action
  id, content_asset_id, platform, published_at,
  result (success|failed|skipped), external_id

social_metrics          -- Engagement data fed back into scoring
  id, publish_log_id, impressions, likes, comments, shares,
  engagement_score, recorded_at

pipeline_runs           -- Health and observability per run
  id, vertical_id, started_at, completed_at, status,
  items_collected, items_scored, items_published, errors (jsonb)
```

---

## Creating Your Vertical

A vertical is a self-contained configuration that tells the engine what to research, how to score it, how to write about it, and where to publish it.

### Step 1: Copy the template

```bash
cp -r python/src/content_engine/verticals/_template \
      python/src/content_engine/verticals/my_brand
```

### Step 2: Configure sources (`sources.yaml`)

```yaml
# sources.yaml — define ALL data sources for this vertical
vertical_id: my_brand
vertical_name: "My Brand Intelligence"

rss_feeds:
  - name: "Industry Publication"
    url: "https://example.com/feed.xml"
    weight: 1.2          # Boost items from this source
  - name: "Competitor Blog"
    url: "https://competitor.com/rss"
    weight: 0.8

search_queries:
  - query: "your industry + trend 2026"
    engine: serper
    results_per_day: 20
  - query: "your product category + news"
    engine: serper
    results_per_day: 15

youtube:
  enabled: true
  search_terms:
    - "your niche keyword"
  channels:
    - "UCxxxxxxxxxxxxxxxx"    # Channel ID of thought leaders

newsletters:
  - email: "digest@publication.com"
    forward_to: "ingest@yourapp.com"
```

### Step 3: Define scoring rubric (`scoring_rubric.yaml`)

```yaml
# scoring_rubric.yaml
dimensions:
  relevance:
    weight: 0.35
    description: "How directly relevant is this to our audience?"
    examples:
      high: "Product announcement in our exact category"
      low:  "General market overview"

  novelty:
    weight: 0.25
    description: "Is this genuinely new information?"

  trend_signal:
    weight: 0.20
    description: "Is this topic gaining or losing momentum?"

  audience_fit:
    weight: 0.15
    description: "Does this serve our specific ICP?"

  risk:
    weight: 0.05
    description: "Factual, reputational, or legal risk"

thresholds:
  auto_approve: 75
  review_queue: 50
  discard: 49

# Automatic discard rules (regardless of score)
auto_discard:
  - contains_phrases: ["sponsored", "press release", "advertisement"]
  - source_domain_blacklist: ["spam-site.com"]
  - older_than_days: 7
```

### Step 4: Write your prompts (`prompts/`)

```
prompts/
├── system_persona.txt       # Who is the AI when writing for this brand?
├── writer_linkedin.txt      # Prompt for LinkedIn post generation
├── writer_newsletter.txt    # Prompt for newsletter section generation
├── writer_blog.txt          # Prompt for long-form blog content
├── scorer.txt               # Scoring reasoning prompt
├── editor.txt               # Editing and quality gate prompt
└── god_synthesis.txt        # Final GOD Mode synthesis prompt
```

**Example `system_persona.txt`:**
```
You are the editorial AI for [Brand Name], a [description of brand].

Your audience is [ICP description].

Your tone is [professional/conversational/analytical/casual].
You always [key brand voice attributes].
You never [forbidden tone/topic attributes].

When writing, prioritize [what matters most to your audience].
```

### Step 5: Configure outputs (`config.yaml`)

```yaml
# config.yaml — master vertical config
vertical_id: my_brand

pipeline:
  schedule: "0 7 * * *"       # Cron: every day at 07:00
  god_mode_enabled: true
  god_mode_threshold: 80       # Only run GOD Mode on items scoring >= 80
  daily_publish_limit: 5       # Max items published per day

outputs:
  linkedin:
    enabled: true
    access_token_env: "LINKEDIN_ACCESS_TOKEN_MYBRAND"
    author_urn_env: "LINKEDIN_AUTHOR_URN_MYBRAND"

  newsletter:
    enabled: true
    esp: resend
    api_key_env: "RESEND_API_KEY"
    from_email: "newsletter@mybrand.com"
    from_name: "My Brand Weekly"
    audience_id: "aud_xxxxxxxx"
    frequency: weekly             # daily | weekly | on_threshold

  blog:
    enabled: false

  report:
    enabled: false

models:
  pre_filter: "anthropic/claude-haiku-3"     # Cheap: bulk pre-filtering
  scoring:    "anthropic/claude-sonnet-4-5"  # Quality: final scoring
  writing:    "anthropic/claude-sonnet-4-5"  # Quality: content generation
  god_mode:   "anthropic/claude-opus-4"      # Premium: deep review only
```

---

## Real-World Vertical Examples

### Example 1: Tech Media Company
**Goal:** Publish daily content about AI, SaaS, and startup news.

```yaml
# Quick config snapshot
sources:
  rss: [TechCrunch, Wired, HN, Product Hunt]
  search: ["AI startup funding", "SaaS product launch"]
  youtube: [MKBHD, Lex Fridman, Y Combinator]

scoring:
  auto_approve: 72
  weights: {relevance: 0.30, novelty: 0.30, trend_signal: 0.25, ...}

outputs: [linkedin, newsletter, blog]
schedule: "0 6 * * 1-5"  # Weekdays at 06:00
```

**Daily cost estimate:** ~$3–6 (500 items → pre-filter → 150 scored → 10 written → 5 published)

---

### Example 2: B2B SaaS Intelligence (e.g., Sponsorship Platform)
**Goal:** Monitor sponsorship deals, creator economy trends, and brand partnership news to generate sales intelligence and content for a sponsorship marketplace.

```yaml
sources:
  rss: [SponsorPulse, Sports Business Journal, Creator Economy Report]
  search: [
    "brand sponsorship deal announcement",
    "creator partnership B2B 2026",
    "sports club sponsor news"
  ]
  youtube: [creator economy channels, agency thought leaders]

scoring:
  weights:
    relevance: 0.40      # Must be about sponsorship/partnership
    novelty: 0.20
    trend_signal: 0.25
    audience_fit: 0.15   # Does this matter to a sports club or creator?

outputs:
  - linkedin: true         # Thought leadership for brand
  - newsletter: true       # Weekly B2B digest for platform users
  - report: true           # Competitive intelligence for sales team
```

**Unique value:** The system tracks which brands are actively spending on sponsorships, which categories are growing, and what pricing benchmarks are emerging — turning raw news into sales intelligence.

---

### Example 3: Industrial B2B Intelligence (e.g., Pallet / Logistics Company)
**Goal:** Monitor supply chain disruptions, wood/timber prices, logistics regulations, competitor activity, and European sustainability directives — producing internal reports and alerts for operations and sales.

```yaml
sources:
  rss: [
    "https://timber-industry-publication.com/rss",
    "https://logistics-europe.eu/feed",
    "https://epal-pallets.org/news/rss"
  ]
  search: [
    "wood pallet price europe 2026",
    "EPAL regulation update",
    "supply chain disruption timber",
    "EUDR deforestation regulation compliance"
  ]
  youtube: []  # disabled — not relevant for this vertical

scoring:
  weights:
    relevance: 0.45      # Strict: must be industry-specific
    risk: 0.25           # High weight: regulations, price shocks matter
    novelty: 0.20
    trend_signal: 0.10

outputs:
  - newsletter: false    # No public newsletter
  - report: true         # Internal weekly operations briefing
  - alert: true          # Immediate Telegram/email alert for P0 signals
                         # (e.g., "new EU regulation affecting EPAL pallets")
```

**Key difference from media vertical:** No public content. The output is internal intelligence: a weekly PDF report for management, and real-time alerts when a critical regulatory or price signal is detected.

---

## Deployment

### Option A: Railway (Recommended for getting started)

1. Connect your GitHub repository to Railway
2. Set all environment variables in the Railway dashboard
3. The cron trigger for `daily_research_pipeline` is configured as a Railway cron job
4. PostgreSQL (Supabase) is your external DB — Railway does not host it

```bash
# railway.toml
[build]
builder = "NIXPACKS"

[[services]]
name = "content-engine-api"
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"

[[services]]
name = "daily-pipeline"
cronSchedule = "0 7 * * *"
startCommand = "python -m content_engine.core.scheduler trigger_daily"
```

### Option B: Render

Deploy backend as a Web Service + a Cron Job service. Free tier is sufficient for single-brand operations.

### Option C: Self-hosted VPS (DigitalOcean, Hetzner)

```bash
# systemd service for the pipeline trigger
[Unit]
Description=Content Engine Daily Pipeline

[Service]
Type=oneshot
WorkingDirectory=/opt/content-engine
ExecStart=/opt/content-engine/venv/bin/python -m content_engine.core.scheduler trigger_daily
EnvironmentFile=/opt/content-engine/.env

[Install]
WantedBy=multi-user.target

# systemd timer (runs daily at 07:00)
[Timer]
OnCalendar=*-*-* 07:00:00
Persistent=true
```

---

## Environment Variables

All secrets are in `.env` (never committed). Copy `.env.example` and fill in your values.

```bash
# .env.example

# Database
DATABASE_URL=postgresql://user:pass@host:5432/content_engine

# LLM Provider (OpenRouter recommended — model-agnostic)
OPENROUTER_API_KEY=sk-or-...

# Research adapters
SERPER_API_KEY=...
YOUTUBE_API_KEY=...         # Google Cloud Console → YouTube Data API v3
FIRECRAWL_API_KEY=...

# Newsletter (Resend)
RESEND_API_KEY=re_...

# Social publishing (one set per vertical/brand)
LINKEDIN_ACCESS_TOKEN_BRAND1=...
LINKEDIN_AUTHOR_URN_BRAND1=urn:li:person:...

# Optional: Monitoring
SENTRY_DSN=...
```

---

## API Cost Model

### Base configuration (single brand, daily pipeline)

| Stage | Model | Items processed | Cost/day |
|-------|-------|-----------------|----------|
| Pre-filter | Claude Haiku | ~500 | ~$0.40 |
| Scoring | Claude Sonnet | ~150 | ~$1.80 |
| Writing | Claude Sonnet | ~10 | ~$0.60 |
| GOD Mode | Claude Opus | ~3 | ~$0.80 |
| **Total** | | | **~$3.60/day** |

### Cost optimization rules

1. **Two-stage scoring:** Pre-filter with a cheap model before premium scoring. This alone reduces costs by 60–70%.
2. **GOD Mode threshold:** Only run the expensive multi-agent review on items scoring ≥ 80. Most days this means 2–5 items.
3. **Daily publish cap:** Set `daily_publish_limit` to prevent runaway writing costs.
4. **Caching:** Research items are cached for 24 hours — no re-scraping of the same URL.
5. **Source weighting:** Give higher weights to your most reliable sources so their items score higher without needing as many LLM tokens to evaluate.

### Scaling (multiple brands)

Each additional vertical adds approximately the same base cost. Running 3 brands simultaneously costs ~$10–12/day — or roughly $300–360/month.

---

## The Feedback Loop

The system improves over time without manual retraining. Here's how:

```
Published content → Platform analytics → Engagement score → Scoring bias update

engagement_score = (
    impressions × 0.10 +
    likes       × 0.30 +
    comments    × 0.40 +
    shares      × 0.20
) / normalization_factor

feedback_bonus = (
    current_bonus × 0.60 +      # Preserve historical learning
    new_engagement × 0.40       # Blend in new signal
)
```

Topics that consistently perform well receive a `feedback_bonus` in future scoring rounds. Over 30–60 days, the system learns what your specific audience responds to — without any manual configuration change.

---

## GOD Mode: Deep Dive

GOD Mode is the quality gate for your most important content. It is expensive (3–4 premium LLM calls per item) so it should be used selectively.

### When GOD Mode fires
- Item's initial score ≥ `god_mode_threshold` (configurable, default 80)
- Item manually flagged for review via dashboard
- Content type is `high_risk` (mentions competitors, legal topics, controversial claims)

### What each sub-agent does

**Advocate:** Reads the draft and builds the strongest case for why this content should be published as-is. Focuses on value, relevance, and timeliness.

**FactCheck:** Receives the draft + Advocate's output. Challenges every claim that could be factually wrong, outdated, or misleading. Produces a list of verified claims, uncertain claims, and disputed claims.

**Creative:** Receives the draft + all previous feedback. Suggests improvements to headline, angle, hook, structure, and CTA. Does not rewrite — only proposes.

**Synthesis:** Integrates all feedback into a final, improved version. Produces the publishable content + a `god_score` that reflects the panel's collective confidence.

### Dependency graph

```
Advocate ──────────────────────────────────────► FactCheck
                                                      │
                                                      ▼
                                                  Creative
                                                      │
Advocate ──── FactCheck ──── Creative ──────────► Synthesis
```

Note: FactCheck and Creative cannot run fully in parallel because Creative depends on FactCheck's output. The only true parallelization opportunity is running FactCheck immediately after Advocate (without waiting). This saves approximately one sequential LLM call time (~3 seconds).

---

## Dashboard

The monitoring dashboard (Next.js) gives you full visibility into every pipeline run.

| Section | What you see |
|---------|-------------|
| **Overview** | Pipeline health, today's run status, items by stage |
| **Ricerca** | All research items collected, by source and date |
| **Scoring** | Score distribution histogram, approved/rejected ratio |
| **Content Hub** | Generated content by platform, edit before publish |
| **Newsletter** | Draft preview, subscriber count, send history |
| **Metriche** | Engagement per item, feedback loop signal |
| **Costi API** | Real-time API spend per model, per day, per vertical |
| **Writing Lab** | A/B test content variants, manual approve/reject |
| **Revenue** | Sponsorship tracking, monetization pipeline |

---

## Frequently Asked Questions

**Q: Do I need to know Python to use this?**
A: To deploy the engine as-is, basic familiarity with Python and command-line tools is enough. To add custom retrievers or modify agent behavior, Python knowledge is required.

**Q: Can I run multiple brands from the same instance?**
A: Yes. Each vertical has its own config, sources, prompts, and credentials. The core engine runs all verticals on the same infrastructure. Each vertical's pipeline runs independently and logs to its own `vertical_id` in the database.

**Q: What if I don't want to publish automatically?**
A: Set `auto_approve_threshold` to 100 in your scoring rubric. All content will go to the review queue in the dashboard, and you approve manually before anything is published.

**Q: Can I use models other than Claude?**
A: Yes. The engine uses OpenRouter as its LLM gateway, which supports 100+ models. Change the model names in `config.yaml` and you can use GPT-4o, Gemini Pro, Mistral, or any other OpenRouter-compatible model.

**Q: What's the minimum setup to get a pipeline running?**
A: You need: a Supabase project (free tier), an OpenRouter API key, a Serper API key, and at least one RSS feed in your `sources.yaml`. Everything else (YouTube, LinkedIn, newsletter) is optional and can be added incrementally.

**Q: How do I handle content in languages other than English?**
A: Set the language in `system_persona.txt` and the writer prompts. The scoring agent will follow the same rubric regardless of language. All LLM models used support multilingual generation.

---

## Contributing

Contributions are welcome. Priority areas:

- New retrievers (Reddit, Substack, X/Twitter, podcasts, patents)
- New output adapters (Instagram, TikTok, Telegram, Slack, email reports)
- Improved semantic deduplication strategies
- Alternative scoring models (fine-tuned classifiers, embeddings-based)
- Pre-built vertical templates (legal, healthcare, finance, real estate)

Please open an issue before submitting a PR for large features.

---

## License

MIT License. Use it, fork it, adapt it to your business.

---

*Built on the learnings from real AI automation experiments. Designed to be the last content infrastructure you build.*
