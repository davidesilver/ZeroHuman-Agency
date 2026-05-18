# Plan: Newsletter Pro

> Source PRD: [GitHub Issue #20 — Newsletter Pro: Multi-provider, AI-generated design, multi-pass copy](https://github.com/davidesilver/ZeroHuman-Agency/issues/20)

## Architectural decisions

Durable decisions that apply across all phases:

- **Routes (Next.js API)**:
  - `POST /api/newsletter/render` — renders layout + content + brand theme → HTML
  - `GET /api/email-provider/lists` — fetches lists from configured provider
  - `POST /api/email-provider/validate` — validates provider API key
  - `GET /api/newsletter/[id]/report` — standardized campaign report
  - `POST /api/webhooks/email/brevo` — Brevo event receiver
  - `POST /api/webhooks/email/mailchimp` — Mailchimp event receiver

- **Routes (Python FastAPI)** — same paths, proxied from Next.js:
  - Existing `/api/newsletter/generate` and `/api/newsletter/send` evolve in place
  - New `/api/webhooks/email/{provider}` receives provider events directly (no proxy)

- **Schema (next migration: 033+)**:
  - New table `email_provider_config`: `(brand_id PK, provider text, api_key_encrypted text, sender_name text, sender_email text, list_id text, webhook_secret text, ab_split_pct int DEFAULT 20, ab_wait_hours int DEFAULT 4, created_at, updated_at)`
  - New table `newsletter_events`: `(id uuid PK, newsletter_id FK, event_type text, email text, occurred_at timestamptz, metadata jsonb, created_at)`
  - Extend `newsletters`: add `provider_campaign_id text`, `layout_type text`, `subject_variant_a text`, `subject_variant_b text`, `ab_winner text`

- **Key models (Python)**:
  - `EmailProvider` ABC — single interface for all providers
  - `CampaignRef` — provider-agnostic campaign reference (provider + campaign_id)
  - `CampaignReport` — standardized metrics dataclass (sent, delivered, opens, clicks, unsubs, rates)
  - `ContactList` / `Subscriber` — standardized list/contact models

- **Auth**: Existing JWT brand-scoped auth unchanged. Webhook endpoints validate via provider-specific mechanisms (Brevo IP whitelist, Mailchimp shared secret)

- **Third-party SDKs**:
  - `brevo-python` v4 for Brevo
  - `mailchimp-marketing` for Mailchimp
  - `resend` (existing) wrapped in adapter
  - `@react-email/components` for template rendering

- **LLM**: Existing `call_llm()` with `task_type="creative"` for generation passes. Budget target: ~$0.05/newsletter across 4 passes.

- **Config precedence** for sender: `email_provider_config` → `brands.from_email/from_name` (migration 024) → `Settings.newsletter_from_email/name` (env vars)

---

## Phase 1: Brevo adapter + Provider Settings UI

**User stories**: #4, #8, #12, #16, #20

### What to build

A brand owner can configure Brevo as their email provider in the Settings page and send an existing newsletter draft through Brevo instead of Resend.

Schema: create `email_provider_config` table (migration 033). Python backend: introduce `EmailProvider` ABC with `create_campaign`, `send_campaign`, `get_lists`, `add_subscribers`, `remove_subscriber` methods. Implement `BrevoProvider` using `brevo-python` v4 SDK and `ResendProvider` wrapping the existing delivery logic. Add a factory `get_email_provider(brand_id)` that reads from `email_provider_config` and falls back to Resend if no provider is configured.

Refactor the existing `send_newsletter()` to route through the adapter instead of calling Resend directly. The existing flow (generate draft → approve → send) remains unchanged — only the delivery layer is swapped.

Next.js: new Settings section "Email Provider" with provider dropdown (Brevo/Resend), API key input, sender name/email, and a list_id dropdown populated after key validation. New API routes: `POST /api/email-provider/validate` (tests the key by calling `get_lists()`), `GET /api/email-provider/lists`.

### Acceptance criteria

- [ ] Migration 033 creates `email_provider_config` table with RLS scoped to brand
- [ ] `EmailProvider` ABC defined with campaign and list management methods
- [ ] `BrevoProvider` creates a campaign via Brevo API and sends it
- [ ] `ResendProvider` wraps existing Resend logic behind the same interface
- [ ] Factory returns correct provider based on brand config, defaults to Resend
- [ ] Settings UI allows configuring Brevo API key and validates it on save
- [ ] Settings UI shows available lists from Brevo after successful validation
- [ ] An existing newsletter draft can be sent through Brevo to a configured list
- [ ] Unit tests mock Brevo API responses and verify adapter translation
- [ ] Brands without provider config continue to use Resend unchanged

---

## Phase 2: React Email templates + brand-themed rendering

**User stories**: #2, #3, #9, #17, #18, #19, #24

### What to build

A professional email template system using React Email that replaces the hardcoded `_build_html()`. The AI will choose the layout in Phase 3; this phase builds the rendering infrastructure and makes all layouts available.

Install `@react-email/components`. Build shared design-system components (EmailHeader, EmailSection, EmailCTA, EmailFooter) that accept a brand theme object (`{ primaryColor, secondaryColor, logoUrl, fontFamily }`). Build three layout components:

- **DigestLayout**: multi-section with thematic grouping, section labels, scan-friendly
- **SingleStoryLayout**: one main piece with deep content, hero image area
- **AnnouncementLayout**: short body, prominent CTA button, urgency-oriented

New API endpoint `POST /api/newsletter/render` accepts `{ layout, content, brand_theme }` and returns `{ html }`. The Python backend calls this endpoint instead of `_build_html()` when generating or previewing newsletters. Add `layout_type` column to `newsletters` table (migration 034).

The newsletter preview modal in the UI now shows the React Email rendered output. Brand theme is read from the `brands` table (existing visual columns from migration 025).

### Acceptance criteria

- [ ] Three React Email layouts render valid, cross-client HTML (inline styles, table fallbacks for Outlook)
- [ ] Brand theme (colors, logo, font) is correctly injected into all layouts
- [ ] `POST /api/newsletter/render` returns HTML for any valid layout + content + theme combination
- [ ] Python backend uses the render endpoint instead of `_build_html()` for both generation and preview
- [ ] Newsletter preview modal displays professionally branded email
- [ ] Migration 034 adds `layout_type` to `newsletters`
- [ ] Snapshot tests cover all three layouts with sample content and brand themes
- [ ] Render endpoint returns 400 for invalid layout names

---

## Phase 3: Multi-pass generator + layout selection + subject variants

**User stories**: #1, #10, #11, #23

### What to build

Refactor `newsletter_generator.py` from a single LLM call into a 4-pass pipeline:

- **Pass 1 (Selection + Layout)**: receives approved research items + brand context + available layouts → returns selected items, chosen layout, section grouping, and editorial rationale
- **Pass 2 (Draft)**: receives structure from Pass 1 + tone rules from memory → generates full copy for each section (title, body, optional CTA)
- **Pass 3 (Refinement)**: receives draft copy → self-critiques for tone alignment, hook quality, readability, section length → outputs revised copy
- **Pass 4 (Subject Variants)**: receives newsletter title + section summaries → generates 2 subject line alternatives optimized for open rate

Each pass uses `call_llm()` with `task_type="creative"` and structured JSON output. The pipeline is fault-tolerant: if Pass 3 fails, Pass 2 output is used; if Pass 4 fails, a single subject from Pass 1 title is used.

Add `subject_variant_a` and `subject_variant_b` columns to `newsletters` (migration 035). The draft review in the newsletter UI shows: the chosen layout with rationale, the refined copy, and both subject line options.

### Acceptance criteria

- [ ] Generator produces content through 4 sequential LLM passes
- [ ] Pass 1 selects a layout from the available set and provides editorial rationale
- [ ] Pass 3 measurably improves copy quality (tone alignment, hook strength)
- [ ] Pass 4 always produces exactly 2 distinct subject line variants
- [ ] If Pass 3 or 4 fails, the pipeline degrades gracefully using earlier pass output
- [ ] Migration 035 adds subject variant columns to `newsletters`
- [ ] Newsletter UI draft review shows layout choice, rationale, and both subject options
- [ ] Integration tests with mocked LLM verify 4-pass chaining and fallback behavior
- [ ] Total LLM cost per newsletter stays within ~$0.05 budget

---

## Phase 4: A/B testing + Analytics + Webhooks

**User stories**: #5, #6, #7, #13, #14, #15, #21

### What to build

End-to-end A/B testing and analytics pipeline. The two subject variants from Phase 3 are used to create an A/B campaign on Brevo.

Extend `BrevoProvider` with `create_ab_campaign(list_id, subjects, html, split_pct, winner_criteria, wait_hours)` that maps to Brevo's `abTesting` API fields. Add `provider_campaign_id` and `ab_winner` columns to `newsletters` (migration 036). The orchestrator calls `create_ab_campaign` when 2 subject variants exist, falling back to `create_campaign` with variant A for the first-ever campaign (Brevo requires at least 1 prior regular send for A/B).

Create `newsletter_events` table (migration 036). Build a FastAPI webhook receiver at `/api/webhooks/email/brevo` that parses Brevo marketing webhook payloads, normalizes events (delivered, opened, clicked, bounced, unsubscribed), and inserts into `newsletter_events`. After insert, update the parent `newsletters` row with aggregated metrics (open_rate, click_rate, unsubscribe_count).

Add `get_report(campaign_ref)` to `BrevoProvider` as a polling fallback — a scheduled task calls it for campaigns sent in the last 48h to catch any missed webhook events.

New Next.js route `GET /api/newsletter/[id]/report` returns the standardized report. The newsletter detail page shows real metrics. The weekly cron job uses the configured provider instead of Resend.

### Acceptance criteria

- [ ] A/B campaign created on Brevo with 2 subjects, configurable split % and wait time
- [ ] First campaign for a brand is sent as regular (not A/B) to satisfy Brevo's prerequisite
- [ ] Migration 036 adds `provider_campaign_id`, `ab_winner` to newsletters and creates `newsletter_events` table
- [ ] Webhook receiver parses Brevo event payloads and inserts normalized events
- [ ] Newsletter metrics (open_rate, click_rate, unsub) update in real-time via webhooks
- [ ] Polling fallback syncs reports for campaigns in the last 48h
- [ ] Newsletter detail page displays campaign analytics with open/click/unsub breakdown
- [ ] A/B winner is recorded after the test period ends
- [ ] Weekly cron uses configured provider for each brand
- [ ] Webhook endpoint validates Brevo source IP for security

---

## Phase 5: Mailchimp adapter + Fallback + Feedback loop

**User stories**: #4 (Mailchimp), #20, #22

### What to build

Second provider implementation and system resilience. Implement `MailchimpProvider` using `mailchimp-marketing` SDK: campaigns use `type="variate"` for A/B with `variate_settings` (winner_criteria, test_size, wait_time, subject_lines). Reports use Mailchimp's `/reports/{id}` endpoint. Lists use `/lists` audience API.

Add Mailchimp webhook receiver at `/api/webhooks/email/mailchimp` with shared-secret validation. Settings UI now shows Mailchimp as a provider option.

Implement provider fallback: if the primary provider's `send_campaign()` or `create_ab_campaign()` throws after retries, the orchestrator falls back to `ResendProvider` (simple send, no A/B) and logs the fallback event. The newsletter record notes which provider actually delivered.

Build the feedback loop: during Pass 4 (subject variant generation), the generator queries past `newsletter_events` to extract patterns — which subject styles had higher open rates for this brand. This context is injected into the subject generation prompt so the system improves over time.

### Acceptance criteria

- [ ] `MailchimpProvider` creates regular and variate campaigns via Mailchimp API
- [ ] Mailchimp A/B uses `variate_settings` with subject_lines and winner_criteria
- [ ] Mailchimp reports are fetched and normalized into `CampaignReport` format
- [ ] Mailchimp webhook receiver validates shared secret and inserts events
- [ ] Settings UI supports Mailchimp configuration with API key validation
- [ ] Provider fallback triggers automatically on primary provider failure
- [ ] Fallback delivery via Resend succeeds and records which provider was used
- [ ] Subject generation prompt includes past campaign performance data
- [ ] Generated subject lines evolve based on historical open rate patterns
- [ ] Unit tests mock Mailchimp API responses and verify adapter translation
