# Plan: Light-Mode-First Rebuild + Creative Cherry-Picks

> Source: Template audit of 72 designs from awesome-design-md + user requirements

## Architectural decisions

Durable decisions that apply across all phases:

- **Canvas**: Warm cream `#f5f1ec` (Intercom reference), NOT pure white — reduces fatigue for long sessions
- **Surface ladder**: 4 steps going *lighter* (cream → white → slightly-tinted-white → pure-white), inverted from the dark ladder
- **Ink hierarchy**: Dark ink on light — `#111111` primary, descending through gray tiers
- **Hairlines**: Light gray borders visible on cream/white (inverted from dark `#23252a`)
- **Coral accent**: `#FF7F50` preserved as the SINGLE chromatic accent — works on both light and dark
- **Sidebar**: Stays **dark** (contrast anchor, Sentry/YouTube Studio pattern), cream main content area
- **Shadows**: Re-introduced for light mode — Miro warm purple-tinted `rgba(5,0,56,0.08)` replaces the dark-mode hairline-only strategy
- **Typography**: Linear spec preserved (Inter, negative tracking, 600 weight headlines). Add Stripe `tnum` for metrics
- **Radius**: Expand to Figma-inspired 16px cards / 8px buttons / 24px featured areas (from current 8/8/12)
- **Pastel tints**: Notion 6-color system for content type/status differentiation on cards
- **No dark mode support**: Light-mode-first, single mode (mirrors previous dark-only approach)

---

## Phase 1: Token Inversion — Light-Mode globals.css

**User stories**: As a user, I see a warm, cream-based light interface instead of the dark obsidian canvas.

### What to build

Rewrite the `:root` token block in `globals.css` from dark values to light values. The `@theme inline` block and utility classes stay structurally identical — only the values change.

**New token values:**

| Token | Dark (current) | Light (new) | Reference |
|-------|---------------|-------------|-----------|
| `--canvas` | `#050505` | `#f5f1ec` | Intercom cream |
| `--surface-1` | `#0f1011` | `#ffffff` | White cards on cream |
| `--surface-2` | `#141516` | `#f9f8f6` | Slightly warm white |
| `--surface-3` | `#18191a` | `#f3f0eb` | Deeper cream (popovers) |
| `--surface-4` | `#191a1b` | `#ede9e3` | Deepest tint |
| `--ink` | `#f7f8f8` | `#111111` | Charcoal (Intercom) |
| `--ink-muted` | `#d0d6e0` | `#4a4a4a` | |
| `--ink-subtle` | `#8a8f98` | `#737373` | |
| `--ink-tertiary` | `#62666d` | `#a3a3a3` | |
| `--hairline` | `#23252a` | `#e5e2dc` | Warm gray border |
| `--hairline-strong` | `#34343a` | `#d1cdc6` | Focus borders |
| `--hairline-tertiary` | `#3e3e44` | `#c4bfb8` | Nested |
| `--primary-foreground` | `#050505` | `#ffffff` | White text on coral |
| `--sidebar` | `var(--canvas)` | `#1a1a2e` | Dark sidebar anchor |
| `--sidebar-foreground` | `var(--ink)` | `#e0e0e0` | Light text on dark sidebar |

Also update:
- Status-soft utility rgba backgrounds (higher opacity for light: 10% instead of 15%)
- `.chip-coral` text color: `#ffffff` instead of `var(--canvas)`
- Selection color: keep coral tint but darker text
- Scrollbar colors: light gray
- Body background & foreground via the same token references
- Comment header: remove "No light mode" rule, update design system description

### Acceptance criteria

- [ ] All `:root` tokens produce a warm cream light theme
- [ ] Sidebar tokens point to a separate dark palette (not canvas)
- [ ] Status-soft utilities readable on light backgrounds
- [ ] `.eyebrow`, `.chip-coral` visually correct on cream
- [ ] `::selection`, `::-webkit-scrollbar`, `:focus-visible` adapted for light
- [ ] No hardcoded dark-mode hex values remain in `:root`
- [ ] TypeScript compiles cleanly

---

## Phase 2: UI Primitive Components

**User stories**: As a user, buttons, badges, inputs, tabs, and cards look polished and readable on the light canvas.

### What to build

Update the 5 core UI primitives to work with the inverted token values:

**`button.tsx`**:
- Default (coral fill): `text-white` instead of `text-[var(--canvas)]` since canvas is now cream
- Outline: `bg-white` + hairline border on cream canvas (shadow-free depth)
- Ghost: hover to `surface-1` (white) — visible on cream
- Focus rings: coral outline still works, adjust opacity

**`badge.tsx`**:
- Default (coral): white text
- Secondary: `surface-2` is now warm-white — needs hairline border for visibility
- Outline: border visible on cream

**`input.tsx`**:
- Background: `surface-1` (white) on cream canvas
- Border: hairline (warm gray) — visible
- Focus: hairline-strong + coral outline
- Placeholder: ink-tertiary (light gray on white)

**`tabs.tsx`**:
- Default pill-toggle: `surface-1` (white) list bg, `surface-2` active tab — may need border
- Line variant: hairline bottom border visible on cream

**`card.tsx`**:
- Default: white bg (`surface-1`) on cream canvas + Miro warm shadow instead of hairline-only
- Featured: `surface-2` (warm-white) for differentiation
- Add optional shadow utility: `shadow-warm` using `rgba(5,0,56,0.08)` (Miro)

### Acceptance criteria

- [ ] All 5 UI components render correctly on cream canvas
- [ ] Coral accent buttons have sufficient contrast (WCAG AA)
- [ ] Input focus states visible
- [ ] Tab selection states distinguishable
- [ ] Cards have warm shadow depth on light mode
- [ ] Build passes

---

## Phase 3: Layout Shell — Sidebar, Staging Bar, URL Bar

**User stories**: As a user, I see a dark sidebar (navigation anchor) contrasting with a light cream main content area.

### What to build

**`sidebar.tsx`**:
- Keep dark: use sidebar-specific tokens (`--sidebar: #1a1a2e`, a deep navy-black)
- Active item: coral left-border + `sidebar-accent` bg
- Hover: slightly lighter surface
- Logo: coral "Z" square mark stays, adjust background if needed
- Eyebrow group labels: light ink-subtle on dark bg

**`staging-bar.tsx`**:
- Coral bg stays (brand signature) — verify text contrast on light page
- May need subtle bottom shadow to separate from cream content area

**`url-bar.tsx`**:
- Input: white bg on cream context bar
- Play button: coral, white icon
- Context bar bg: `surface-2` or `surface-3` for subtle separation from content

**`layout.tsx`**:
- Main content area: cream canvas bg
- Sidebar: dark bg via sidebar tokens
- Verify the flex layout still works with the color contrast

### Acceptance criteria

- [ ] Dark sidebar with coral accents renders correctly
- [ ] Staging bar separates cleanly from light content
- [ ] URL bar input visible on light context bar
- [ ] Layout flex structure correct with mixed light/dark zones
- [ ] No color bleeding between sidebar and main areas

---

## Phase 4: Dashboard + All 14 Page Views

**User stories**: As a user, every page in the dashboard is readable and polished on the light cream canvas.

### What to build

**Dashboard page** (`page.tsx`):
- `.chip-coral` on h1: white text on coral (verify)
- `.eyebrow`: `ink-subtle` on cream = mid-gray, readable
- KPI cards: white cards with warm shadow on cream
- Pipeline card: white bg, arrow separators
- Activity/Agent tables: white card, warm borders

**KPI card** (`kpi-card.tsx`):
- White card on cream, warm shadow
- Value text: `ink` (#111111) — high contrast
- Destructive variant: red border visible on white
- Trend chip: status-success-soft on white card (verify contrast)

**Remaining 14 pages** (content-hub, calendario, metriche, memory, newsletter, settings/*, setup, social, writing-lab, ricerca, blog, brands, revenue, costi-api):
- All use the same token system — most will "just work" after Phase 1-3
- Verify: status-soft badges, platform badges, icons with brand-primary color
- Fix any remaining dark-mode assumptions (e.g., white text where dark text needed)

### Acceptance criteria

- [ ] Dashboard renders fully on cream canvas — all sections readable
- [ ] KPI values have strong contrast on white cards
- [ ] All 14 page views render without broken colors
- [ ] Status badges (success/warning/error/info) readable on light
- [ ] Tables, forms, modals all adapted
- [ ] Full build: 68 pages, 0 errors

---

## Phase 5: Creative Cherry-Picks

**User stories**: As a user, I see a visually distinctive, editorially-inspired dashboard that feels like a premium content tool — not a generic SaaS app.

### What to build

**1. Notion pastel card tint system** — 6 content-type tints:

| Content type | Tint | Hex | Reference |
|-------------|------|-----|-----------|
| Draft | Lavender | `#e6e0f5` | Notion |
| In Review | Peach | `#ffe8d4` | Notion |
| Approved | Mint | `#d9f3e1` | Notion |
| Scheduled | Sky | `#dcecfa` | Notion |
| Published | Cream-gold | `#fef7d6` | Notion |
| Error/Rejected | Rose | `#fde0ec` | Notion |

Add as CSS utilities: `.tint-draft`, `.tint-review`, `.tint-approved`, `.tint-scheduled`, `.tint-published`, `.tint-error`

Apply to: draft-card.tsx backgrounds, calendar event dots, pipeline stage backgrounds, status chips.

**2. Stripe tabular figures** — add `font-feature-settings: "tnum"` to:
- KPI card values
- Table cells with numbers (metrics, costs, counts)
- Any `font-mono` numeric display

**3. Starbucks press animation** — add `.press` utility:
```css
.press:active { transform: scale(0.97); transition: transform 80ms; }
```
Apply to: primary CTA buttons, card clickable areas.

**4. Figma generous card radius** — update radius scale:
- Cards: 16px (up from 12px) for standard, 24px for featured/modal
- Keep buttons at 8px (Linear spec)
- Add `--radius-card: 16px` and `--radius-featured: 24px` tokens

**5. Miro warm shadow system** — replace hairline-only depth:
```css
--shadow-sm: 0 1px 3px rgba(5, 0, 56, 0.06);
--shadow-md: 0 4px 12px rgba(5, 0, 56, 0.08);
--shadow-lg: 0 8px 24px rgba(5, 0, 56, 0.10);
```
Apply to: card.tsx default, popovers, modals, floating elements.
Purple-tinted shadows feel warmer than black shadows on cream.

### Acceptance criteria

- [ ] 6 pastel tint utilities defined and applied to content cards
- [ ] KPI numbers align in columns (tabular figures active)
- [ ] Buttons have tactile press animation
- [ ] Cards use 16px radius, featured areas 24px
- [ ] Warm purple-tinted shadows on all elevated surfaces
- [ ] Visual harmony between cream canvas, white cards, pastel tints, warm shadows
- [ ] Full build clean
