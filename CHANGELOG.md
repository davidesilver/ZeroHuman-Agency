# Changelog

## [1.0.0] — 2026-06-12

First stable release. ZeroHuman is a self-hosted AI content team: research → score → draft → multi-agent review → publish, with social metrics feeding back into scoring weights. Nothing publishes without your approval.

### Added
- **Automated shorts pipeline** — TTS, word-level subtitles, b-roll media sourcing, and a shorts generator with reusable artifacts, plus Docker sidecars for TTS and Whisper (`--profile video`)
- Redesigned onboarding setup wizard with custom dialog modals
- Demo GIF and social preview image
- `docs/launch/` drafts and a "Why not just Postiz or n8n?" comparison in the README
- StagingBar toggle via `NEXT_PUBLIC_STAGING_BAR`

### Changed
- README repositioned: compose-first quickstart, approval-gate framing, creator-focused audience
- `.env.example` synced with all actual environment variables
- Consolidated database schema (`supabase/schema_complete.sql`) as the canonical setup path

### Fixed
- `setup.sh` and the quickstart now pass `.env.local` to compose interpolation — frontend build args were silently blank
- idna CVE-2026-45409 patched; disputed pyjwt PYSEC-2025-183 suppressed
- Brand deletion RLS bug bypass; JSX lint entities; MCP detect handler typing

## [0.2.0] — 2026-05

Internal milestone: multi-tenant content pipeline (research, scoring, Writer→Editor drafts, GOD-mode review, humanizer, newsletter, Postiz publishing, Telegram bot, observability).
