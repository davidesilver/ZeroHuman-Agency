# Plan: OSS Quality Audit Remediation

> Source: Code review, accessibility audit, and documentation audit — 2026-05-19

## Architectural decisions

Durable decisions that apply across all phases:

- **Backend port**: `8000` is the canonical port for the Python backend (dev and prod). The README Quick Start previously used `8082` — this is a bug.
- **Python version**: `>=3.14` per `pyproject.toml`. All docs must match.
- **Migration range**: `001-042` (49 files, gap at 003). All docs must use this range.
- **Frontend validation**: Zod is the chosen schema library (aligns with shadcn/ui ecosystem).
- **Test framework (frontend)**: Vitest + React Testing Library (Next.js 16 standard).
- **Accessibility target**: WCAG 2.1 AA compliance.
- **Italian directory rename**: `ricerca/` → `research/`, `metriche/` → `metrics/`. Route paths change accordingly.

---

## Phase 1: Documentation emergency fixes

**Issues**: D1, D3, D4, D5, D9, D10

### What to build

Fix all factually wrong content across documentation — leaked local paths, wrong ports, wrong Python version, inconsistent migration counts, wrong CORS origins. These are the changes that would embarrass the project if a contributor reads them today.

### Acceptance criteria

- [ ] `python/README.md` uses relative paths (`../docs/SETUP.md` etc.), no `/Users/claw/` anywhere in the repo
- [ ] All references to backend port use `8000` (README Quick Start section updated)
- [ ] README states Python `3.14+` (not `3.11+`)
- [ ] All docs reference migration range `001-042` consistently
- [ ] README `ALLOWED_ORIGINS` example uses port `3000` (not `3080`)
- [ ] `OPEN_SOURCE_PREPARATION_SUMMARY.md` either removed or updated: `plans/` existence acknowledged, `supabase/MIGRATIONS_LIST.md` path corrected to `docs/database/MIGRATIONS_LIST.md`
- [ ] `grep -r '/Users/claw' .` returns zero matches (excluding `.claude/`, `.git/`)

---

## Phase 2: OSS governance files

**Issues**: D2, CONTRIBUTING.md gaps

### What to build

Add the standard open-source governance files that every credible OSS project needs: a Code of Conduct and a security vulnerability disclosure policy. Update CONTRIBUTING.md to reference both.

### Acceptance criteria

- [ ] `CODE_OF_CONDUCT.md` at repo root (Contributor Covenant v2.1)
- [ ] `SECURITY.md` at repo root describing: supported versions, how to report vulnerabilities (email), response timeline, what qualifies as a vulnerability
- [ ] `CONTRIBUTING.md` links to `CODE_OF_CONDUCT.md`
- [ ] `CONTRIBUTING.md` links to `SECURITY.md` for security-related contributions
- [ ] README links to CONTRIBUTING.md and CODE_OF_CONDUCT.md

---

## Phase 3: Documentation consistency pass

**Issues**: D6, D7, D8, D13, D14

### What to build

Fix all internal inconsistencies, broken links, and stale content in the `/docs/` directory. This is a single pass through every doc that references schemas, migrations, or section numbers.

### Acceptance criteria

- [ ] `docs/SETUP.md` section numbering is sequential (no duplicate 3, 10, 11)
- [ ] `docs/SETUP.md` internal link to MIGRATIONS_LIST.md points to `docs/database/MIGRATIONS_LIST.md`
- [ ] `docs/SETUP.md` cross-reference to "section 9 (credential vault)" is correct
- [ ] `docs/database/MIGRATIONS_LIST.md` includes migrations 034-042 with descriptions
- [ ] `docs/database/SCHEMA.md` includes tables from migrations 030-042 (feature_flags, brand_integrations, brevo_*, deep_research_jobs, competitor_snapshots, video_*, heygen_usage, email_automations, llm_provider_metrics)
- [ ] `docs/security/SECRET-ROTATION.md` includes Fernet key (`BRAND_SECRETS_ENCRYPTION_KEY`) rotation procedure
- [ ] `docs/database/QUICKSTART_CRON.md` no longer advises putting secrets directly in migration files; uses env var or Supabase Vault reference instead
- [ ] `docs/database/QUICKSTART_CRON.md` broken `/references/docs/cron-jobs.md` link removed or updated

---

## Phase 4: Frontend error handling & type safety

**Issues**: P1, P2, P3, S3

### What to build

Replace silent error swallowing with user-visible feedback. Type all `any` usage. Fix API routes that accept malformed JSON silently.

### Acceptance criteria

- [ ] `settings/page.tsx` system config fetch shows an error state (not infinite loading) after timeout or failure
- [ ] `settings/page.tsx` OpenClaw share fetch failure surfaces in UI (toast or inline error)
- [ ] `settings/agenti/page.tsx` all 7 `console.error` calls replaced with user-facing toast/banner + optional console.error for dev
- [ ] `settings/page.tsx:571` uses `router.refresh()` instead of `window.location.reload()`
- [ ] `deep-research/page.tsx` — all 3 `any` types replaced with proper interfaces (research source, idea item)
- [ ] API routes (`research/trigger`, `content/generate`, `scoring/run`, `images/generate`, `images/carousel`, `feature-flags`, `social/integrations/mine`, `social/publish`) return 400 on malformed JSON body instead of proceeding with empty data
- [ ] No new `any` types introduced
- [ ] `tsc --noEmit` passes

---

## Phase 5: Accessibility — critical (WCAG A)

**Issues**: A1, A2, A3, A6

### What to build

Fix all WCAG 2.1 Level A violations. These are the issues that make the app unusable for assistive technology users. This phase focuses on screen reader semantics and keyboard operability.

### Acceptance criteria

- [ ] All interactive custom components (StatusBadge, ProviderDot, ModelChip, status tiles, time-window buttons) have `aria-label` or visible text alternatives
- [ ] OpenClaw range slider (`settings/page.tsx`) has an associated `<label>` or `aria-label="OpenClaw traffic share percentage"`
- [ ] All `<label>` elements without `htmlFor` are either wrapped around their input or given `htmlFor` pointing to the input's `id`
- [ ] Color-only status indicators (green/amber dots) include `sr-only` text span (e.g., "Configured", "Not set")
- [ ] Dashboard layout has a skip-to-content link as the first focusable element: `<a href="#main-content" className="sr-only focus:not-sr-only ...">Skip to content</a>`
- [ ] `<main>` element in dashboard layout has `id="main-content"`
- [ ] Manual screen reader test (VoiceOver) can navigate the settings page and understand all status indicators

---

## Phase 6: Accessibility — AA compliance

**Issues**: A4, A5, A7, A8

### What to build

Achieve WCAG 2.1 AA compliance: minimum text sizes, verified color contrast, consistent focus indicators, and semantic HTML throughout.

### Acceptance criteria

- [ ] No `text-[10px]` remains in the codebase — minimum font size is `text-[11px]` (12px equivalent at default browser settings) or `text-xs` (Tailwind's 12px)
- [ ] `text-[11px]` instances reviewed — any body text promoted to `text-xs`; only supplementary metadata/labels may use `text-[11px]`
- [ ] Color contrast audit: `text-muted-foreground` on all background variants meets 4.5:1 ratio (use browser DevTools or axe)
- [ ] All `<button>` elements (including time-window selectors, icon-only buttons) have visible `focus:ring` or `focus:outline` styles
- [ ] All dashboard sub-pages use semantic HTML: `<header>` for page title area, `<section>` for card groups, `<main>` inherited from layout
- [ ] Automated accessibility scan (axe-core or Lighthouse) on settings page returns 0 critical/serious violations

---

## Phase 7: Italian directory rename

**Issues**: D11, D12

### What to build

Rename Italian-language routes and directories to English for international OSS contributor clarity. This is a breaking change for bookmarks and any external links.

### Acceptance criteria

- [ ] `src/app/(dashboard)/ricerca/` renamed to `src/app/(dashboard)/research/`
- [ ] `src/app/(dashboard)/metriche/` renamed to `src/app/(dashboard)/metrics/`
- [ ] All internal `<Link href=` references updated (`/ricerca` → `/research`, `/metriche` → `/metrics`)
- [ ] Sidebar navigation labels updated (if they show Italian text)
- [ ] API routes or proxy paths referencing these pages updated
- [ ] `README.md` project structure section reflects new names
- [ ] Italian fragments in `docs/plans/2026-05-15-integration-candidates-triage.md` translated to English
- [ ] No broken links when navigating the dashboard
- [ ] `grep -rn 'ricerca\|metriche' src/` returns zero matches (excluding git history)

---

## Phase 8: Frontend validation & security hardening

**Issues**: S1, S2

### What to build

Add Zod schema validation to all frontend forms and evaluate CSRF protection needs. Document the security decision.

### Acceptance criteria

- [ ] `zod` added as a dependency
- [ ] Brand creation form (`settings/page.tsx`) validates with Zod schema: name (1-100 chars, no empty), slug (lowercase alphanumeric + hyphens, 1-60 chars), topics (optional array), budget (optional positive number)
- [ ] Validation errors shown inline next to the offending field
- [ ] At least 3 other forms with user input validated with Zod (image-generation settings, social connections, agent creation)
- [ ] CSRF evaluation documented in `docs/security/` — either: (a) "not needed because all mutations use Bearer token auth via fetch, not cookie-based form submissions" or (b) CSRF token implementation added
- [ ] No form submits user input to the backend without frontend validation

---

## Phase 9: Frontend test foundation

**Issues**: D15

### What to build

Set up the frontend testing infrastructure and write initial tests for critical user flows. This creates the foundation for test coverage going forward.

### Acceptance criteria

- [ ] Vitest + React Testing Library + jsdom configured in `vitest.config.ts`
- [ ] `npm test` script added to `package.json` and runs Vitest
- [ ] CI workflow updated to run frontend tests alongside `tsc` and `eslint`
- [ ] Tests written for at least 5 critical paths:
  - Brand creation form: validates inputs, submits, shows error on failure
  - Settings page: renders health overview, handles config fetch failure gracefully
  - Content hub: renders draft list, filters work
  - Deep research: submits query, displays results
  - Sidebar: renders navigation links, highlights active route
- [ ] All tests pass in CI
- [ ] Test coverage report configured (optional but recommended)
