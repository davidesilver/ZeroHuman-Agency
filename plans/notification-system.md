# Plan: Notification System — Telegram Lifecycle Alerts, Daily Digest, Bot Commands & Activity Feed

> Source PRD: [Issue #24](https://github.com/davidesilver/ZeroHuman-Agency/issues/24)

## Architectural decisions

Durable decisions that apply across all phases:

- **Routes (Next.js proxy)**: `/api/webhooks/telegram` (POST, no JWT — Telegram-to-server), `/api/activity` (GET, JWT auth)
- **Routes (Python)**: `/api/webhooks/telegram` (POST), `/api/activity` (GET, paginated)
- **Schema**: New table `notification_events` — `id` (uuid PK), `brand_id` (FK), `event_type` (text), `severity` (text: info/success/warning/error), `title` (text), `detail` (jsonb), `entity_type` (text nullable), `entity_id` (text nullable), `created_at` (timestamptz)
- **Key models**: `NotificationEvent` (Pydantic), `NotificationService` (class with `emit_event()`, `send_digest()`, `send_lifecycle_alert()`), `TelegramBot` (class with command parsing and execution)
- **Auth**: Telegram webhook validated via `X-Telegram-Bot-Api-Secret-Token` header + `chat_id` match against configured value. Activity feed endpoint uses standard JWT auth via `proxyToBackend`. Bot commands only accepted from configured `chat_id`.
- **Third-party boundary**: Telegram Bot API only (`sendMessage`, `setWebhook`). No other notification channels.
- **Severity routing**: `error` and `warning` → immediate Telegram alert. `success` → immediate Telegram alert (lifecycle events). `info` → digest-only (batched).
- **Best-effort principle**: All notification calls are wrapped in try/except. Telegram failures are logged but never block the pipeline.

---

## Phase 1: Event Log + Daily Digest

**User stories**: 1, 2, 8, 17, 22, 23

### What to build

The foundation: a `notification_events` database table, a `NotificationService` class that can persist events and compose digest messages, and integration into the scheduler so that a daily digest is sent via Telegram at the end of each brand's pipeline run.

All existing `send_telegram_alert()` call sites are migrated to `notification_service.emit_event()`, which both persists the event and routes it to the appropriate channel based on severity. The old `send_telegram_alert()` function becomes a thin internal method of the service.

The digest message is sent per-brand, formatted with emoji prefixes and sections for research, scoring, drafts, and newsletters. When everything succeeds, the message explicitly states "no issues ✅" to resolve the silent ambiguity problem.

### Acceptance criteria

- [ ] Migration creates `notification_events` table with all required columns and indexes on `brand_id` and `created_at`
- [ ] `NotificationService.emit_event()` persists an event row and sends an immediate Telegram alert for `warning`/`error` severity
- [ ] `NotificationService.send_digest()` queries events since the last digest, groups by category, and sends a formatted Telegram message
- [ ] Scheduler calls `send_digest()` at the end of `daily_research_pipeline()` for the brand
- [ ] All existing `send_telegram_alert()` call sites (scheduler, god_system, llm_client, fallback_monitor, newsletter_generator) migrated to `emit_event()`
- [ ] Digest message sent even when all steps succeed, with explicit "no issues" indicator
- [ ] Telegram API failures are logged but do not raise exceptions or block the pipeline
- [ ] One digest message per brand (not aggregated across brands)

---

## Phase 2: Lifecycle Alerts (Campaign Sent, A/B Winner, Spikes, Failures)

**User stories**: 3, 4, 5, 6, 7, 15, 16, 26

### What to build

Extend the event emission to cover the newsletter lifecycle stages that are currently silent: campaign sent, A/B winner declared, unsubscribe spike detection, and provider send failure. Also migrate cost cap exceeded to the notification system.

Each lifecycle alert is sent immediately via Telegram with consistent formatting: emoji prefix, brand label, key metrics, and a deep link to the relevant dashboard page (e.g., `/newsletter/{id}`).

Unsubscribe spike detection is implemented as a simple threshold check: when processing webhook events, if the unsubscribe count for a newsletter exceeds 2× the brand's average unsubscribe rate, an alert is emitted.

### Acceptance criteria

- [ ] `newsletter_delivery.send_campaign()` emits a `campaign_sent` event with recipient count, provider name, and subject lines
- [ ] Webhook event processing emits `ab_winner_declared` event when A/B test resolves, including winner subject, both open rates
- [ ] Webhook event processing detects unsubscribe spikes (>2× brand average) and emits `unsubscribe_spike` event
- [ ] Campaign send failures emit `campaign_send_failed` event with provider error details
- [ ] Cost cap exceeded alert migrated to `emit_event()` with `error` severity
- [ ] All lifecycle alert messages include a deep link to the dashboard entity
- [ ] Alert messages use consistent format: emoji prefix, brand name, key metrics, link
- [ ] Events are persisted in `notification_events` (available for Phase 4 activity feed)

---

## Phase 3: Telegram Bot Commands

**User stories**: 9, 10, 11, 12, 13, 14, 24, 25

### What to build

A Telegram bot that receives webhook POSTs from the Telegram Bot API, parses text commands, executes the corresponding action against the database/services, and replies with a confirmation or error message.

The webhook route is `/api/webhooks/telegram` — Next.js proxies the raw body to Python (same pattern as Brevo/Mailchimp webhooks). The Python handler validates the webhook secret header and the sender's `chat_id`, then dispatches to the appropriate command handler.

Supported commands:
- `/approve <draft_id>` — sets draft status to "approved"
- `/send <newsletter_id>` — triggers newsletter campaign send
- `/skip <item_id>` — sets research item status to "skipped"
- `/discard <draft_id>` — sets draft status to "discarded"
- `/status` — returns aggregated pipeline state across all brands (last run time, pending drafts, scheduled newsletters, provider health)

Each command replies to the Telegram chat with a confirmation message or a descriptive error if the ID is invalid or the action cannot be performed.

### Acceptance criteria

- [ ] Next.js route `/api/webhooks/telegram` forwards raw POST body to Python backend
- [ ] Python handler validates `X-Telegram-Bot-Api-Secret-Token` header
- [ ] Python handler rejects messages from non-configured `chat_id`
- [ ] `/approve <id>` updates draft status and replies with confirmation
- [ ] `/send <id>` triggers newsletter send pipeline and replies with confirmation
- [ ] `/skip <id>` updates research item status and replies with confirmation
- [ ] `/discard <id>` updates draft status to discarded and replies with confirmation
- [ ] `/status` returns formatted summary of all brands: last run, pending drafts, scheduled newsletters, provider status
- [ ] Invalid IDs produce a clear error reply (not a crash)
- [ ] Missing arguments produce a help message for that command
- [ ] Unknown commands produce a general help message listing available commands
- [ ] Telegram webhook URL registration documented in setup instructions

---

## Phase 4: Dashboard Activity Feed

**User stories**: 18, 19, 20, 21

### What to build

A Python endpoint (`GET /api/activity`) that returns paginated `notification_events` from the database, a Next.js proxy route, and a React component on the dashboard homepage that renders the event list.

The endpoint supports `limit` (default 50), `offset`, and optional `brand_id` filter parameters. Events are returned sorted by `created_at` descending.

The frontend component renders each event as a row with: severity-colored icon (green/yellow/red/blue), relative timestamp ("3h ago"), brand badge, event title, and a link to the entity if `entity_type` and `entity_id` are present. No real-time updates — the feed loads on page visit and is sufficient given the operator's low visit frequency.

### Acceptance criteria

- [ ] Python endpoint `GET /api/activity` returns paginated events with `limit`, `offset`, `brand_id` params
- [ ] Next.js proxy `/api/activity` forwards to Python with JWT auth
- [ ] Dashboard homepage includes an activity feed component below existing content
- [ ] Events display with severity-colored icons (success=green, warning=yellow, error=red, info=blue)
- [ ] Events show relative timestamps (e.g., "3h ago", "yesterday")
- [ ] Events show brand name as a badge when multiple brands exist
- [ ] Events with `entity_type` and `entity_id` link to the relevant dashboard page
- [ ] Feed shows last 50 events by default, sorted newest first
- [ ] Empty state shows "No recent activity" message

---

## Phase 5: Test Suite

**User stories**: all (cross-cutting validation)

### What to build

Comprehensive tests for all new Python modules: `NotificationService`, `TelegramBot`, and the event log query layer. Tests use pytest-asyncio (existing project pattern) and mock external boundaries (Telegram API via httpx mock, Supabase via mock client).

Tests verify external behavior through public interfaces, not internal implementation details. Message formatting tests assert on structure (sections present, emoji prefixes, required fields) not exact string matching.

### Acceptance criteria

- [ ] NotificationService: test `emit_event()` routing by severity (immediate vs digest-only)
- [ ] NotificationService: test `send_digest()` message composition for all-success, partial-failure, and zero-items scenarios
- [ ] NotificationService: test graceful degradation when Telegram API returns error/timeout
- [ ] NotificationService: test message formatting includes required sections and deep links
- [ ] TelegramBot: test command parsing for all 5 commands with valid input
- [ ] TelegramBot: test rejection of messages from unauthorized `chat_id`
- [ ] TelegramBot: test webhook secret validation (valid, missing, wrong)
- [ ] TelegramBot: test error replies for invalid IDs and missing arguments
- [ ] TelegramBot: test `/status` aggregation across multiple brands
- [ ] EventLog: test event persistence and retrieval by brand
- [ ] EventLog: test digest query (events since last digest, grouped by category)
- [ ] EventLog: test activity feed pagination (limit, offset, ordering)
- [ ] All tests pass with `pytest` from the project root
