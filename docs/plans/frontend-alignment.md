# Plan: Frontend Alignment

> Source PRD: docs/plans/2026-05-15-capability-expansion-prd-v2.md
> Context: Post-implementation audit found that all 16 backend phases are built, but the dashboard has critical gaps in navigation, error handling, brand isolation, and component reuse.

## Architectural decisions

Durable decisions that apply across all phases:

- **Navigation**: `src/lib/navigation.ts` is the single source for sidebar items. New sections: RESEARCH (deep-research, competitor-watch), VIDEO (videos), with existing sections reorganized.
- **Feature flags in UI**: Read via `src/lib/feature-flags.ts` (Supabase direct read). Pages gated by flag show a "Feature not enabled" card instead of rendering the full UI.
- **Brand context**: All capability pages must call `useBrand()` from `@/lib/brand-context` and pass `activeBrand.id` to API calls. Pages render a "Select a brand" prompt if no brand is active.
- **Error pattern**: Shared `useAsyncFetch()` hook returns `{ data, loading, error, refetch }`. Error state renders a standardized `<ErrorCard />` component.
- **Polling pattern**: Shared `usePolling(callback, intervalMs)` hook handles setInterval + cleanup + visibility API pause.
- **Status badge**: Shared mapping in `src/lib/status-colors.ts` consumed by all async-job pages.

---

## Phase 1: Navigation & discoverability

**User stories**: All capabilities reachable from sidebar without knowing URL

### What to build

Add missing pages to the sidebar navigation in `src/lib/navigation.ts`. Organize into logical sections matching the capability groups. The sidebar becomes the single entry point to all features.

New navigation structure:
- **PRODUCTION**: Research, Deep Research, Calendar, Newsletter, Blog, Social
- **VIDEO & MEDIA**: Videos, Competitor Watch
- **QUALITY**: Writing Lab, Metrics
- **SYSTEM**: Memory, Revenue, API Costs, Brands, Settings

### Acceptance criteria

- [ ] `/deep-research` appears in sidebar under PRODUCTION or RESEARCH section
- [ ] `/competitor-watch` appears in sidebar
- [ ] `/videos` appears in sidebar under VIDEO & MEDIA section
- [ ] `/content-hub` appears in sidebar (was already missing)
- [ ] Active state highlights correctly on each new link
- [ ] No broken nav links — all href match existing `page.tsx` files
- [ ] Sidebar remains scrollable on small viewports

---

## Phase 2: Feature flag gating UI

**User stories**: "Feature flags per-brand, default OFF" — capabilities must not be visible/usable until explicitly enabled per brand

### What to build

A `<FeatureGate flag="video_enabled">` wrapper component that:
1. Reads the flag value for the active brand (client-side via `/api/feature-flags?key=...`)
2. Shows children if flag is ON
3. Shows a "Feature not enabled for this brand" card with admin instructions if OFF
4. Shows nothing (or a skeleton) while loading

Apply `<FeatureGate>` to: deep-research page, competitor-watch page, videos page, audience page, automations page.

### Acceptance criteria

- [ ] `<FeatureGate>` component exists in `src/components/ui/`
- [ ] Deep Research page gated by `deep_research_enabled`
- [ ] Competitor Watch page gated by `competitor_monitoring_enabled`
- [ ] Videos page gated by `video_enabled`
- [ ] Audience + Automations pages gated by `email_marketing_enabled`
- [ ] When flag is OFF, page shows explanatory card (not blank)
- [ ] When flag is ON, page renders normally with zero layout shift

---

## Phase 3: Error handling & resilience

**User stories**: Platform degrades gracefully when services are unavailable

### What to build

1. A `useAsyncFetch(url, options?)` hook that wraps `fetch` with:
   - `loading`, `error`, `data` state
   - Automatic retry (1x) on network error
   - `refetch()` function
2. An `<ErrorCard message={string} onRetry={fn} />` component for consistent error display
3. Apply to all 6 new capability pages (deep-research, competitor-watch, videos, audience, automations, video-templates)

### Acceptance criteria

- [ ] `useAsyncFetch` hook created in `src/hooks/`
- [ ] `<ErrorCard>` component created
- [ ] Deep Research shows error card if API unreachable
- [ ] Competitor Watch shows error card if API unreachable
- [ ] Videos shows error card if render API fails
- [ ] Audience shows error card if Brevo key check fails
- [ ] Automations shows error on create/toggle failure
- [ ] Video Templates shows error on create failure
- [ ] All error cards have a "Retry" button

---

## Phase 4: Brand isolation enforcement

**User stories**: Multi-tenancy — every operation scoped to active brand

### What to build

Ensure all new capability pages read `activeBrand` from context and:
1. Show a "Select a brand first" prompt if no brand is active
2. Pass `brand_id` explicitly to API calls (via query param or header)
3. Reset state when brand switches (listen to brand context changes)

Pages to fix: deep-research, competitor-watch, videos, automations.

### Acceptance criteria

- [ ] All 4 pages call `useBrand()` and read `activeBrand`
- [ ] If `activeBrand` is null, a "Select a brand" card is shown instead of the form
- [ ] Brand switch triggers data reload (useEffect dependency on `activeBrand.id`)
- [ ] API calls include brand context (already handled by `proxyToBackend` via cookie, but page state resets)

---

## Phase 5: Shared components extraction

**User stories**: Maintainability — DRY common patterns across async-job pages

### What to build

Extract duplicated patterns into reusable components/hooks:

1. **`usePolling(callback, intervalMs)`** hook — replaces 3 identical useEffect+setInterval patterns
2. **`src/lib/status-colors.ts`** — single status→badge-variant mapping (`pending`, `running`, `completed`, `failed`)
3. **`<AsyncJobCard>`** component — title, subtitle, timestamp, status badge, optional expand button, optional spinner
4. **`<EmptyState icon={} message={} action?={} />`** component

Refactor deep-research, competitor-watch, and videos pages to use these shared pieces.

### Acceptance criteria

- [ ] `usePolling` hook in `src/hooks/use-polling.ts`
- [ ] `status-colors.ts` in `src/lib/`
- [ ] `<AsyncJobCard>` component in `src/components/ui/`
- [ ] `<EmptyState>` component in `src/components/ui/`
- [ ] Deep Research page uses `usePolling` + `AsyncJobCard`
- [ ] Competitor Watch page uses `usePolling` + `AsyncJobCard`
- [ ] Videos page uses `usePolling` + `AsyncJobCard`
- [ ] No functional regressions (pages look and behave identically)

---

## Phase 6: Settings dead-links fix

**User stories**: All settings sub-pages discoverable from Settings hub

### What to build

Add navigation cards/links in `settings/page.tsx` for the two orphaned sub-pages:
1. Email Automations → `/settings/automations` (under the existing Brevo section)
2. Video Templates → `/settings/video-templates` (new Video section in settings)

### Acceptance criteria

- [ ] Settings page shows "Email Automations" card with link to `/settings/automations`
- [ ] Settings page shows "Video Templates" card with link to `/settings/video-templates`
- [ ] Both links use consistent card styling matching existing settings links
- [ ] Cards appear in logical position (automations near Brevo, video templates near video section)

---

## Phase 7: Feature flags admin panel

**User stories**: Operator can enable/disable capabilities per-brand without SQL access

### What to build

A new settings sub-page `/settings/feature-flags` that:
1. Lists all known flags for the active brand with their current value
2. Allows toggling each flag ON/OFF
3. Shows flag descriptions (from a hardcoded registry matching Python's `feature_flags.py` constants)
4. Saves via POST to `/api/feature-flags`

Add a link from the main Settings page.

### Acceptance criteria

- [ ] Page at `/settings/feature-flags/page.tsx` exists
- [ ] Shows all flags: `video_enabled`, `email_marketing_enabled`, `deep_research_enabled`, `competitor_monitoring_enabled`
- [ ] Each flag has a toggle switch and description
- [ ] Toggle saves immediately via API
- [ ] Success/error feedback shown on toggle
- [ ] Settings main page links to this sub-page
- [ ] Only accessible to brand owner/admin (enforced by existing RLS)
