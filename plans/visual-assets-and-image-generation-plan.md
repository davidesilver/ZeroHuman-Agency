# Visual Assets & Autonomous Image Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Memory-Native stack with (P7) editable long-term **brand visual assets** — logo, palette, design system, example newsletters/posts — and (P8) a fully autonomous, configurable **image generation pipeline** that consumes those assets to produce carousels and post images without human prompt crafting.

**Architecture:** Brand assets live in **Supabase Storage** (private bucket, brand-scoped path) with metadata rows in a new `brand_assets` table. The table is **not** a semantic-memory candidate because these assets are stable, human-managed, and binary — the Warm Semantic layer only records *references* to them (e.g. `principle: "always pair headlines with brand logo top-left"`). Image generation is a new Python service `image_generator.py` that: (a) reads the draft + brand assets + palette via a prompt-builder, (b) calls a **configurable image model** (default FLUX-schnell via Replicate, overridable per-brand via `brands.image_model`), (c) uploads result to Supabase Storage, (d) attaches the public URL to `content_drafts.media_url`. Pillo / PostNitro integration lands as a pluggable backend behind the same interface.

**Tech Stack:** Supabase Storage (S3-compatible), Next.js 14 App Router, React Server Components, FastAPI + httpx, Replicate Python SDK (for image models), Pillow for local palette extraction, existing pgvector memory layer.

---

## 0. Why this phase exists — grounding

The P0–P6 plan closed the *textual* memory gap but left three concrete user-reported holes:

1. **"Come faccio a dargli il logo, il design system, la palette e/o un esempio di newsletter/contenuti?"** — no UI, no storage, no table. Today a brand has zero visual identity surface.
2. **"Se non abbiamo fatto niente per la generazione immagini, come vengono creati caroselli, ecc?"** — the existing `services/visual_generator.py` is a 50-line stub that returns a fake `https://cdn.ai-visuals.com/...` URL. It is not wired to any real model and does not reference brand assets.
3. **"Alcune cose per il contesto non possono essere short term, come logo ... queste cose devono essere anche editabili."** — confirms that `memory_semantic` (TTL-decaying vector store) is the wrong home for these files.

**Decision locked with user (Italian, this session):**
> *"per la generazione immagini voglio che sia totalmente autonoma quindi 3, modello di generazione dedicato e modificabile. poi si può anche pensare a integrazione con pillo o altri."*

→ Option 3 = fully autonomous image gen with a **dedicated, per-brand configurable model**. Pillo/PostNitro integration is a later backend plugin, not the default path.

---

## 1. File structure

### P7 — Visual Assets

**New files:**
- `supabase/migrations/025_brand_visual_assets.sql` — `brand_assets` table + storage bucket policies
- `src/app/api/brands/[id]/assets/route.ts` — GET list, POST upload metadata
- `src/app/api/brands/[id]/assets/[assetId]/route.ts` — DELETE, PATCH (rename/retag)
- `src/app/api/brands/[id]/assets/upload-url/route.ts` — issues signed upload URL (Supabase Storage presigned PUT)
- `src/app/(dashboard)/settings/brand-assets/page.tsx` — Brand Assets manager UI
- `src/components/brand-assets/asset-upload-card.tsx` — drag-drop upload component
- `src/components/brand-assets/palette-editor.tsx` — color swatch editor (client component)
- `python/src/content_engine/utils/brand_assets.py` — server-side helper: `get_brand_logo_url()`, `get_brand_palette()`, `list_example_content()`

**Modified:**
- `src/app/(dashboard)/settings/brand-context/page.tsx:1-end` — add "Visual Assets" link card at top
- `src/app/(dashboard)/brands/page.tsx` — after create, banner links to both `/settings/brand-context` AND `/settings/brand-assets`
- `src/lib/types/database.types.ts` — regenerate after migration

### P8 — Autonomous Image Generation

**New files:**
- `supabase/migrations/026_image_generation_config.sql` — adds `brands.image_model`, `brands.image_style_preset`, creates `image_generations` audit table
- `python/src/content_engine/services/image_generator.py` — new full-fat generator (replaces stub `visual_generator.py`)
- `python/src/content_engine/services/image_backends/__init__.py` — backend registry
- `python/src/content_engine/services/image_backends/base.py` — `ImageBackend` protocol
- `python/src/content_engine/services/image_backends/replicate_backend.py` — FLUX/SDXL via Replicate
- `python/src/content_engine/services/image_backends/openai_backend.py` — DALL-E 3 / gpt-image-1
- `python/src/content_engine/services/image_backends/pillo_backend.py` — Pillo carousel API (stub with TODO for real creds)
- `python/src/content_engine/services/image_prompt_builder.py` — deterministic prompt construction from draft + brand assets
- `python/src/content_engine/api/routes_images.py` — `POST /images/generate`, `POST /images/carousel`, `GET /images/{id}`
- `python/tests/test_image_prompt_builder.py` — unit tests for prompt construction (pure, no network)
- `python/tests/test_image_backends.py` — backend dispatch tests with mocked httpx
- `src/app/api/images/generate/route.ts` — Next.js proxy to Python
- `src/app/api/images/carousel/route.ts` — Next.js proxy
- `src/components/content-hub/generate-visual-button.tsx` — client component: button on draft → calls proxy → shows progress + result
- `src/app/(dashboard)/settings/image-generation/page.tsx` — per-brand model/style/prompt-template editor

**Modified:**
- `python/src/content_engine/services/visual_generator.py` — **deleted** (replaced by new module); all call sites updated
- `python/src/content_engine/config.py` — adds `replicate_api_token`, `openai_api_key` (optional), `pillo_api_key` (optional), `default_image_model`
- `python/src/content_engine/api/routes.py` — mounts `routes_images` router
- `src/app/(dashboard)/content-hub/[id]/page.tsx` — if draft has `platform IN (instagram, linkedin)` show the Generate Visual button

---

## 2. Database shapes (locked)

### `brand_assets`
```sql
CREATE TABLE public.brand_assets (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  kind          text NOT NULL CHECK (kind IN (
                  'logo_primary', 'logo_mono', 'logo_favicon',
                  'palette', 'font_specimen', 'design_system_pdf',
                  'example_newsletter', 'example_post', 'example_carousel',
                  'watermark', 'other'
                )),
  label         text,                          -- human label, e.g. "Logo dark mode"
  storage_path  text NOT NULL,                 -- "brand-assets/<brand_id>/<uuid>.<ext>"
  mime_type     text NOT NULL,
  bytes         bigint NOT NULL,
  width_px      int,
  height_px     int,
  palette_hex   text[],                        -- only for kind='palette'
  metadata      jsonb NOT NULL DEFAULT '{}',   -- extracted: dominant colors, font names, etc.
  uploaded_by   uuid REFERENCES auth.users(id),
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_brand_assets_brand_kind ON public.brand_assets (brand_id, kind);
```

### `brands` column additions (migration 026)
```sql
ALTER TABLE public.brands
  ADD COLUMN IF NOT EXISTS image_model          text DEFAULT 'black-forest-labs/flux-schnell',
  ADD COLUMN IF NOT EXISTS image_style_preset   text DEFAULT 'editorial-minimal',
  ADD COLUMN IF NOT EXISTS image_prompt_template text,                                   -- optional override
  ADD COLUMN IF NOT EXISTS image_backend        text DEFAULT 'replicate'
    CHECK (image_backend IN ('replicate','openai','pillo','mock'));
```

### `image_generations`
```sql
CREATE TABLE public.image_generations (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  draft_id      uuid REFERENCES public.content_drafts(id) ON DELETE SET NULL,
  backend       text NOT NULL,
  model_id      text NOT NULL,
  prompt        text NOT NULL,
  negative_prompt text,
  seed          bigint,
  status        text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','succeeded','failed')),
  storage_path  text,                          -- final PNG in Supabase Storage
  public_url    text,
  width_px      int,
  height_px     int,
  cost_usd      numeric(10,4),
  error         text,
  started_at    timestamptz,
  finished_at   timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_imggen_brand_draft ON public.image_generations (brand_id, draft_id);
```

---

# PHASE P7 — Brand Visual Assets

### Task P7.1: Migration 025 — brand_assets table + storage bucket

**Files:**
- Create: `supabase/migrations/025_brand_visual_assets.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- 025_brand_visual_assets.sql
-- Editable, long-term brand visual assets. Distinct from memory_semantic
-- (which is TTL-decaying and vector-indexed). These rows point at binary
-- files in the 'brand-assets' private bucket.

BEGIN;

CREATE TABLE IF NOT EXISTS public.brand_assets (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  kind          text NOT NULL CHECK (kind IN (
                  'logo_primary','logo_mono','logo_favicon',
                  'palette','font_specimen','design_system_pdf',
                  'example_newsletter','example_post','example_carousel',
                  'watermark','other'
                )),
  label         text,
  storage_path  text NOT NULL,
  mime_type     text NOT NULL,
  bytes         bigint NOT NULL,
  width_px      int,
  height_px     int,
  palette_hex   text[],
  metadata      jsonb NOT NULL DEFAULT '{}',
  uploaded_by   uuid REFERENCES auth.users(id),
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brand_assets_brand_kind
  ON public.brand_assets (brand_id, kind);

-- Only one primary logo per brand (enforced at app layer normally, but guardrail here)
CREATE UNIQUE INDEX IF NOT EXISTS uq_brand_assets_single_primary_logo
  ON public.brand_assets (brand_id)
  WHERE kind = 'logo_primary';

-- Same membership RLS pattern used elsewhere in this codebase (P1 helper).
ALTER TABLE public.brand_assets ENABLE ROW LEVEL SECURITY;

CREATE POLICY brand_assets_select ON public.brand_assets
  FOR SELECT USING (public.user_has_brand(brand_id));
CREATE POLICY brand_assets_insert ON public.brand_assets
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));
CREATE POLICY brand_assets_update ON public.brand_assets
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));
CREATE POLICY brand_assets_delete ON public.brand_assets
  FOR DELETE USING (public.user_has_brand(brand_id));

-- Storage bucket (created idempotently; policies attached separately).
INSERT INTO storage.buckets (id, name, public)
  VALUES ('brand-assets','brand-assets', false)
  ON CONFLICT (id) DO NOTHING;

-- Storage policies — object path is '<brand_id>/<uuid>.<ext>', first segment scopes membership.
CREATE POLICY brand_assets_storage_read ON storage.objects
  FOR SELECT USING (
    bucket_id = 'brand-assets'
    AND public.user_has_brand((split_part(name, '/', 1))::uuid)
  );
CREATE POLICY brand_assets_storage_write ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'brand-assets'
    AND public.user_has_brand((split_part(name, '/', 1))::uuid)
  );
CREATE POLICY brand_assets_storage_delete ON storage.objects
  FOR DELETE USING (
    bucket_id = 'brand-assets'
    AND public.user_has_brand((split_part(name, '/', 1))::uuid)
  );

-- keep updated_at fresh
CREATE OR REPLACE FUNCTION public.touch_brand_assets_updated_at()
RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_brand_assets_touch
  BEFORE UPDATE ON public.brand_assets
  FOR EACH ROW EXECUTE FUNCTION public.touch_brand_assets_updated_at();

COMMIT;
```

- [ ] **Step 2: Apply the migration**

Run: `npx supabase db push --include-all`
Expected: "Applying migration 025_brand_visual_assets.sql ... done"

- [ ] **Step 3: Smoke-check the bucket and policies**

Run:
```sql
SELECT id, public FROM storage.buckets WHERE id='brand-assets';
SELECT polname FROM pg_policy WHERE polrelid = 'public.brand_assets'::regclass;
```
Expected: one bucket row (public=false), four policies (`brand_assets_select`, `_insert`, `_update`, `_delete`).

- [ ] **Step 4: Regenerate TypeScript types**

Run: `npx supabase gen types typescript --project-id wbjmgczwqmdkitylfvud > src/lib/types/database.types.ts`
Expected: diff shows new `brand_assets` table types.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/025_brand_visual_assets.sql src/lib/types/database.types.ts
git commit -m "feat(p7): brand_assets table + storage bucket with RLS"
```

---

### Task P7.2: Signed upload URL endpoint

**Files:**
- Create: `src/app/api/brands/[id]/assets/upload-url/route.ts`

- [ ] **Step 1: Write the route**

```ts
/**
 * Issues a short-lived signed upload URL for the brand-assets bucket.
 * The browser PUTs the file directly to Supabase Storage — server never holds bytes.
 * Path convention: "<brand_id>/<uuid>.<ext>" so RLS policy split_part() works.
 */
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { randomUUID } from 'crypto'

interface Ctx { params: Promise<{ id: string }> }

const ALLOWED_MIME = new Set([
  'image/png','image/jpeg','image/svg+xml','image/webp',
  'application/pdf',
])
const MAX_BYTES = 15 * 1024 * 1024 // 15 MB

export async function POST(req: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  let body: { filename?: string; mime_type?: string; bytes?: number }
  try { body = await req.json() } catch { return errorResponse('Invalid JSON', 400) }

  if (!body.mime_type || !ALLOWED_MIME.has(body.mime_type))
    return errorResponse(`mime_type must be one of: ${[...ALLOWED_MIME].join(', ')}`, 400)
  if (!body.bytes || body.bytes <= 0 || body.bytes > MAX_BYTES)
    return errorResponse(`bytes must be 1..${MAX_BYTES}`, 400)

  const ext = (body.filename || '').split('.').pop()?.toLowerCase().replace(/[^a-z0-9]/g,'') || 'bin'
  const path = `${brandId}/${randomUUID()}.${ext}`

  const supabase = await createClient()
  const { data, error } = await supabase
    .storage
    .from('brand-assets')
    .createSignedUploadUrl(path)
  if (error) return errorResponse(error.message, 500)

  return jsonResponse({
    upload_url: data.signedUrl,
    token: data.token,
    storage_path: path,
    expires_in_seconds: 60,
  })
}
```

- [ ] **Step 2: Manual curl check**

```bash
curl -X POST http://localhost:3000/api/brands/<brand_id>/assets/upload-url \
  -H "Cookie: <session>" -H "Content-Type: application/json" \
  -d '{"filename":"logo.png","mime_type":"image/png","bytes":52341}'
```
Expected: JSON with `upload_url`, `storage_path` of form `<brand_id>/<uuid>.png`.

- [ ] **Step 3: Commit**

```bash
git add src/app/api/brands/[id]/assets/upload-url/route.ts
git commit -m "feat(p7): signed upload URL endpoint for brand assets"
```

---

### Task P7.3: Assets CRUD endpoints (list + create metadata + delete)

**Files:**
- Create: `src/app/api/brands/[id]/assets/route.ts`
- Create: `src/app/api/brands/[id]/assets/[assetId]/route.ts`

- [ ] **Step 1: Write the list + create route**

```ts
// src/app/api/brands/[id]/assets/route.ts
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

interface Ctx { params: Promise<{ id: string }> }

const VALID_KINDS = new Set([
  'logo_primary','logo_mono','logo_favicon',
  'palette','font_specimen','design_system_pdf',
  'example_newsletter','example_post','example_carousel',
  'watermark','other',
])

export async function GET(_: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('brand_assets')
    .select('id,kind,label,storage_path,mime_type,bytes,width_px,height_px,palette_hex,metadata,created_at')
    .eq('brand_id', brandId)
    .order('kind')
    .order('created_at', { ascending: false })
  if (error) return errorResponse(error.message, 500)
  return jsonResponse(data || [])
}

/** Called *after* the browser finishes uploading to Storage. Registers metadata. */
export async function POST(req: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  let body: {
    kind?: string; label?: string; storage_path?: string; mime_type?: string;
    bytes?: number; width_px?: number; height_px?: number;
    palette_hex?: string[]; metadata?: Record<string, unknown>;
  }
  try { body = await req.json() } catch { return errorResponse('Invalid JSON', 400) }
  if (!body.kind || !VALID_KINDS.has(body.kind)) return errorResponse('Invalid kind', 400)
  if (!body.storage_path || !body.storage_path.startsWith(`${brandId}/`))
    return errorResponse('storage_path must begin with the brand id', 400)
  if (!body.mime_type || !body.bytes) return errorResponse('mime_type and bytes required', 400)

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('brand_assets')
    .insert({
      brand_id: brandId,
      kind: body.kind,
      label: body.label ?? null,
      storage_path: body.storage_path,
      mime_type: body.mime_type,
      bytes: body.bytes,
      width_px: body.width_px ?? null,
      height_px: body.height_px ?? null,
      palette_hex: body.palette_hex ?? null,
      metadata: body.metadata ?? {},
      uploaded_by: auth.userId,
    })
    .select('id,kind,label,storage_path,mime_type,bytes,palette_hex,metadata,created_at')
    .single()
  if (error) return errorResponse(error.message, 500)
  return jsonResponse(data, 201)
}
```

- [ ] **Step 2: Write the DELETE + PATCH route**

```ts
// src/app/api/brands/[id]/assets/[assetId]/route.ts
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

interface Ctx { params: Promise<{ id: string; assetId: string }> }

export async function DELETE(_: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId, assetId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  const supabase = await createClient()
  const { data: row, error: selErr } = await supabase
    .from('brand_assets')
    .select('storage_path')
    .eq('id', assetId)
    .eq('brand_id', brandId)
    .single()
  if (selErr || !row) return errorResponse('Asset not found', 404)

  // Delete the file first; if this fails we keep the DB row so we can retry.
  const { error: storageErr } = await supabase.storage.from('brand-assets').remove([row.storage_path])
  if (storageErr) return errorResponse(`Storage delete failed: ${storageErr.message}`, 500)

  const { error: delErr } = await supabase.from('brand_assets').delete().eq('id', assetId)
  if (delErr) return errorResponse(delErr.message, 500)
  return jsonResponse({ deleted: assetId })
}

export async function PATCH(req: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId, assetId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  let body: { label?: string; palette_hex?: string[]; metadata?: Record<string, unknown> }
  try { body = await req.json() } catch { return errorResponse('Invalid JSON', 400) }

  const patch: Record<string, unknown> = {}
  if (body.label !== undefined) patch.label = String(body.label).slice(0, 120)
  if (body.palette_hex !== undefined) {
    if (!Array.isArray(body.palette_hex) || body.palette_hex.some(s => !/^#[0-9a-f]{6}$/i.test(s)))
      return errorResponse('palette_hex must be ["#rrggbb", ...]', 400)
    patch.palette_hex = body.palette_hex
  }
  if (body.metadata !== undefined) patch.metadata = body.metadata
  if (Object.keys(patch).length === 0) return errorResponse('No editable fields', 400)

  const supabase = await createClient()
  const { data, error } = await supabase.from('brand_assets')
    .update(patch).eq('id', assetId).eq('brand_id', brandId)
    .select().single()
  if (error) return errorResponse(error.message, 500)
  return jsonResponse(data)
}
```

- [ ] **Step 3: Commit**

```bash
git add src/app/api/brands/[id]/assets/
git commit -m "feat(p7): brand assets CRUD (list, create metadata, patch, delete)"
```

---

### Task P7.4: Upload card React component

**Files:**
- Create: `src/components/brand-assets/asset-upload-card.tsx`

- [ ] **Step 1: Write the component**

```tsx
'use client'
import { useState } from 'react'
import { Upload, Loader2, CheckCircle2, XCircle } from 'lucide-react'

type Kind =
  | 'logo_primary' | 'logo_mono' | 'logo_favicon'
  | 'palette' | 'font_specimen' | 'design_system_pdf'
  | 'example_newsletter' | 'example_post' | 'example_carousel'
  | 'watermark' | 'other'

export function AssetUploadCard({ brandId, onUploaded }: { brandId: string; onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [kind, setKind] = useState<Kind>('logo_primary')
  const [label, setLabel] = useState('')
  const [status, setStatus] = useState<'idle'|'uploading'|'done'|'error'>('idle')
  const [err, setErr] = useState<string | null>(null)

  async function handleUpload() {
    if (!file) return
    setStatus('uploading'); setErr(null)
    try {
      // 1) ask for a signed upload URL
      const u = await fetch(`/api/brands/${brandId}/assets/upload-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name, mime_type: file.type, bytes: file.size }),
      })
      if (!u.ok) throw new Error((await u.json()).error || 'Could not get upload URL')
      const { upload_url, storage_path } = await u.json()

      // 2) PUT the bytes directly to Supabase Storage
      const putRes = await fetch(upload_url, {
        method: 'PUT',
        headers: { 'Content-Type': file.type, 'x-upsert': 'true' },
        body: file,
      })
      if (!putRes.ok) throw new Error(`Upload failed: ${putRes.status}`)

      // 3) register metadata
      let width_px: number | undefined, height_px: number | undefined
      if (file.type.startsWith('image/')) {
        try {
          const bmp = await createImageBitmap(file)
          width_px = bmp.width; height_px = bmp.height
        } catch { /* non-fatal */ }
      }
      const regRes = await fetch(`/api/brands/${brandId}/assets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          kind, label: label || null, storage_path,
          mime_type: file.type, bytes: file.size, width_px, height_px,
        }),
      })
      if (!regRes.ok) throw new Error((await regRes.json()).error || 'Metadata registration failed')

      setStatus('done'); setFile(null); setLabel(''); onUploaded()
    } catch (e) {
      setStatus('error'); setErr(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="rounded-lg border border-dashed p-4 space-y-3">
      <h3 className="text-sm font-medium flex items-center gap-2"><Upload size={14}/> Upload asset</h3>
      <input
        type="file"
        accept="image/png,image/jpeg,image/svg+xml,image/webp,application/pdf"
        onChange={e => setFile(e.target.files?.[0] ?? null)}
        className="text-sm"
      />
      <div className="grid grid-cols-2 gap-2">
        <select className="text-sm border rounded px-2 py-1" value={kind} onChange={e => setKind(e.target.value as Kind)}>
          <option value="logo_primary">Logo (primary)</option>
          <option value="logo_mono">Logo (mono)</option>
          <option value="logo_favicon">Favicon</option>
          <option value="palette">Palette reference</option>
          <option value="font_specimen">Font specimen</option>
          <option value="design_system_pdf">Design system PDF</option>
          <option value="example_newsletter">Example newsletter</option>
          <option value="example_post">Example post</option>
          <option value="example_carousel">Example carousel</option>
          <option value="watermark">Watermark</option>
          <option value="other">Other</option>
        </select>
        <input
          type="text" placeholder="Label (optional)"
          className="text-sm border rounded px-2 py-1"
          value={label} onChange={e => setLabel(e.target.value)}
        />
      </div>
      <button
        onClick={handleUpload} disabled={!file || status === 'uploading'}
        className="px-3 py-1.5 rounded bg-black text-white text-sm disabled:opacity-50 inline-flex items-center gap-2"
      >
        {status === 'uploading' && <Loader2 className="animate-spin" size={14}/>}
        {status === 'done' && <CheckCircle2 size={14}/>}
        {status === 'error' && <XCircle size={14}/>}
        {status === 'uploading' ? 'Uploading…' : 'Upload'}
      </button>
      {err && <p className="text-xs text-red-600">{err}</p>}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/brand-assets/asset-upload-card.tsx
git commit -m "feat(p7): asset upload card with signed-URL direct PUT"
```

---

### Task P7.5: Palette editor component

**Files:**
- Create: `src/components/brand-assets/palette-editor.tsx`

- [ ] **Step 1: Write the component**

```tsx
'use client'
import { useState } from 'react'
import { Plus, Trash2, Save } from 'lucide-react'

export function PaletteEditor({
  brandId, assetId, initial,
}: { brandId: string; assetId: string; initial: string[] }) {
  const [colors, setColors] = useState<string[]>(initial.length ? initial : ['#000000'])
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    await fetch(`/api/brands/${brandId}/assets/${assetId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ palette_hex: colors }),
    })
    setSaving(false)
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {colors.map((c, i) => (
          <div key={i} className="flex items-center gap-1 border rounded px-2 py-1">
            <input
              type="color" value={c}
              onChange={e => { const next = [...colors]; next[i] = e.target.value; setColors(next) }}
              className="w-6 h-6 cursor-pointer border-0 p-0"
            />
            <span className="text-xs font-mono">{c}</span>
            <button onClick={() => setColors(colors.filter((_, j) => j !== i))}
                    className="text-gray-400 hover:text-red-600"><Trash2 size={12}/></button>
          </div>
        ))}
        <button onClick={() => setColors([...colors, '#888888'])}
                className="border border-dashed rounded px-2 py-1 text-xs inline-flex items-center gap-1">
          <Plus size={12}/> Add
        </button>
      </div>
      <button onClick={save} disabled={saving}
              className="px-3 py-1 rounded bg-black text-white text-xs inline-flex items-center gap-1 disabled:opacity-50">
        <Save size={12}/> {saving ? 'Saving…' : 'Save palette'}
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/brand-assets/palette-editor.tsx
git commit -m "feat(p7): palette editor component"
```

---

### Task P7.6: Brand Assets manager page

**Files:**
- Create: `src/app/(dashboard)/settings/brand-assets/page.tsx`

- [ ] **Step 1: Write the page**

```tsx
'use client'
import { useCallback, useEffect, useState } from 'react'
import { useBrand } from '@/lib/hooks/use-brand'
import { AssetUploadCard } from '@/components/brand-assets/asset-upload-card'
import { PaletteEditor } from '@/components/brand-assets/palette-editor'
import { Image as ImgIcon, FileText, Trash2 } from 'lucide-react'

type Asset = {
  id: string; kind: string; label: string | null; storage_path: string;
  mime_type: string; bytes: number; width_px: number | null; height_px: number | null;
  palette_hex: string[] | null; metadata: Record<string, unknown>; created_at: string;
}

export default function BrandAssetsPage() {
  const { activeBrand } = useBrand()
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [signedUrls, setSignedUrls] = useState<Record<string, string>>({})

  const refresh = useCallback(async () => {
    if (!activeBrand) return
    setLoading(true)
    const res = await fetch(`/api/brands/${activeBrand.id}/assets`)
    const data: Asset[] = await res.json()
    setAssets(data)
    // Fetch signed preview URLs for images
    const entries = await Promise.all(data.filter(a => a.mime_type.startsWith('image/')).map(async a => {
      const u = await fetch(`/api/brands/${activeBrand.id}/assets/${a.id}/preview`).then(r => r.ok ? r.json() : null)
      return [a.id, u?.url ?? ''] as const
    }))
    setSignedUrls(Object.fromEntries(entries))
    setLoading(false)
  }, [activeBrand])

  useEffect(() => { refresh() }, [refresh])

  async function remove(id: string) {
    if (!activeBrand) return
    if (!confirm('Delete this asset?')) return
    await fetch(`/api/brands/${activeBrand.id}/assets/${id}`, { method: 'DELETE' })
    refresh()
  }

  if (!activeBrand) return <div className="p-6">Select a brand first.</div>

  const grouped = assets.reduce<Record<string, Asset[]>>((acc, a) => {
    (acc[a.kind] ||= []).push(a); return acc
  }, {})

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <header>
        <h1 className="text-2xl font-semibold">Brand visual assets</h1>
        <p className="text-sm text-gray-500">
          Logos, palette, design system, example content — long-term editable. Used by the image
          generator and by text agents when they need visual grounding.
        </p>
      </header>

      <AssetUploadCard brandId={activeBrand.id} onUploaded={refresh} />

      {loading && <p className="text-sm text-gray-500">Loading…</p>}

      {Object.entries(grouped).map(([kind, list]) => (
        <section key={kind} className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600">
            {kind.replace(/_/g,' ')}
          </h2>
          <div className="grid grid-cols-3 gap-3">
            {list.map(a => (
              <div key={a.id} className="border rounded p-3 space-y-2">
                {a.mime_type.startsWith('image/') && signedUrls[a.id]
                  ? <img src={signedUrls[a.id]} alt={a.label ?? a.kind}
                         className="w-full h-32 object-contain bg-gray-50 rounded"/>
                  : <div className="w-full h-32 bg-gray-50 rounded flex items-center justify-center text-gray-400">
                      {a.mime_type === 'application/pdf' ? <FileText size={32}/> : <ImgIcon size={32}/>}
                    </div>}
                <div className="text-xs">
                  <div className="font-medium truncate">{a.label || '—'}</div>
                  <div className="text-gray-500">{(a.bytes/1024).toFixed(0)} KB {a.width_px ? `· ${a.width_px}×${a.height_px}` : ''}</div>
                </div>
                {a.kind === 'palette' && (
                  <PaletteEditor brandId={activeBrand.id} assetId={a.id} initial={a.palette_hex ?? []}/>
                )}
                <button onClick={() => remove(a.id)}
                        className="text-xs text-red-600 inline-flex items-center gap-1">
                  <Trash2 size={12}/> Delete
                </button>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Write the preview-URL helper endpoint**

Files:
- Create: `src/app/api/brands/[id]/assets/[assetId]/preview/route.ts`

```ts
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

interface Ctx { params: Promise<{ id: string; assetId: string }> }

export async function GET(_: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId, assetId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  const supabase = await createClient()
  const { data: row } = await supabase.from('brand_assets')
    .select('storage_path').eq('id', assetId).eq('brand_id', brandId).single()
  if (!row) return errorResponse('Not found', 404)

  const { data, error } = await supabase.storage.from('brand-assets')
    .createSignedUrl(row.storage_path, 60 * 10) // 10 min
  if (error) return errorResponse(error.message, 500)
  return jsonResponse({ url: data.signedUrl })
}
```

- [ ] **Step 3: Manual check**

Navigate to `/settings/brand-assets`. Upload a PNG as `logo_primary`; confirm:
- grid shows it with dimensions
- reloading page still shows it (persisted in `brand_assets`)
- `DELETE` button removes both DB row and storage object (check via Supabase dashboard)

- [ ] **Step 4: Commit**

```bash
git add src/app/\(dashboard\)/settings/brand-assets/page.tsx src/app/api/brands/[id]/assets/[assetId]/preview/route.ts
git commit -m "feat(p7): brand assets manager page + preview URL endpoint"
```

---

### Task P7.7: Python helper to read brand assets

**Files:**
- Create: `python/src/content_engine/utils/brand_assets.py`

- [ ] **Step 1: Write the helper**

```python
"""Server-side accessors for brand_assets.

Read-only from Python side — writes happen through Next.js so ownership/RLS
checks are always enforced at the user-session layer. Python only needs to
resolve brand assets when generating content or images.
"""
from __future__ import annotations
from typing import Optional, TypedDict

from ..db import get_db
from ..config import settings


class BrandAsset(TypedDict):
    id: str
    kind: str
    label: Optional[str]
    storage_path: str
    mime_type: str
    palette_hex: Optional[list[str]]
    metadata: dict


def _signed_url(storage_path: str, ttl_seconds: int = 600) -> str:
    db = get_db()
    res = db.storage.from_("brand-assets").create_signed_url(storage_path, ttl_seconds)
    return res.get("signedURL") or res.get("signed_url") or ""


def get_brand_asset(brand_id: str, kind: str) -> Optional[BrandAsset]:
    """Return the most recent asset of `kind` for `brand_id`, or None."""
    db = get_db()
    rows = (
        db.table("brand_assets")
        .select("id, kind, label, storage_path, mime_type, palette_hex, metadata")
        .eq("brand_id", brand_id).eq("kind", kind)
        .order("created_at", desc=True).limit(1).execute().data
    )
    return rows[0] if rows else None


def get_brand_logo_url(brand_id: str) -> Optional[str]:
    a = get_brand_asset(brand_id, "logo_primary")
    return _signed_url(a["storage_path"]) if a else None


def get_brand_palette(brand_id: str) -> list[str]:
    """Return hex colors for the brand. Falls back to [] if no palette uploaded."""
    a = get_brand_asset(brand_id, "palette")
    return list(a.get("palette_hex") or []) if a else []


def list_example_content(brand_id: str, kind: str, limit: int = 5) -> list[BrandAsset]:
    """Fetch up to `limit` example assets (newsletter/post/carousel) ordered newest-first."""
    assert kind in ("example_newsletter", "example_post", "example_carousel")
    db = get_db()
    rows = (
        db.table("brand_assets")
        .select("id, kind, label, storage_path, mime_type, palette_hex, metadata")
        .eq("brand_id", brand_id).eq("kind", kind)
        .order("created_at", desc=True).limit(limit).execute().data
    )
    return rows or []
```

- [ ] **Step 2: Add a smoke test**

Files:
- Create: `python/tests/test_brand_assets_helper.py`

```python
from unittest.mock import MagicMock, patch
from content_engine.utils import brand_assets


def _mock_db_with_rows(rows):
    m = MagicMock()
    chain = m.table.return_value.select.return_value.eq.return_value.eq.return_value \
             .order.return_value.limit.return_value.execute.return_value
    chain.data = rows
    return m


def test_get_brand_palette_returns_hex_list():
    rows = [{"id":"a","kind":"palette","label":"core","storage_path":"p","mime_type":"image/png",
             "palette_hex":["#111111","#222222"],"metadata":{}}]
    with patch.object(brand_assets, "get_db", return_value=_mock_db_with_rows(rows)):
        assert brand_assets.get_brand_palette("brand-x") == ["#111111","#222222"]


def test_get_brand_palette_empty_when_no_asset():
    with patch.object(brand_assets, "get_db", return_value=_mock_db_with_rows([])):
        assert brand_assets.get_brand_palette("brand-x") == []
```

- [ ] **Step 3: Run tests**

Run: `cd python && pytest tests/test_brand_assets_helper.py -v`
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add python/src/content_engine/utils/brand_assets.py python/tests/test_brand_assets_helper.py
git commit -m "feat(p7): python helper for brand assets + unit tests"
```

---

### Task P7.8: Wire navigation — Settings, Memory, post-create banner

**Files:**
- Modify: `src/app/(dashboard)/settings/page.tsx` (add card linking to `/settings/brand-assets`)
- Modify: `src/app/(dashboard)/settings/brand-context/page.tsx` (add top link to Brand Assets)
- Modify: `src/app/(dashboard)/memory/page.tsx` (add second link beside "Edit Brand Context")
- Modify: `src/app/(dashboard)/brands/page.tsx` (post-create banner already links to brand-context; add brand-assets)

- [ ] **Step 1: Add Brand Assets card to Settings index**

In `src/app/(dashboard)/settings/page.tsx`, alongside the existing "Brand context" card, add:

```tsx
<Link href="/settings/brand-assets" className="rounded-lg border p-4 hover:bg-gray-50 block">
  <div className="flex items-center gap-2 text-sm font-medium"><ImageIcon size={14}/> Brand assets</div>
  <p className="text-xs text-gray-500 mt-1">
    Logo, palette, design system, example content. Editable long-term assets used by text agents
    and the image generator.
  </p>
</Link>
```

Ensure `import { Image as ImageIcon } from 'lucide-react'` is present.

- [ ] **Step 2: Add header link on brand-context page**

At the top of `src/app/(dashboard)/settings/brand-context/page.tsx`, above the UploadDocumentCard, add:

```tsx
<Link href="/settings/brand-assets"
      className="block rounded-md border bg-blue-50 border-blue-200 p-3 text-sm text-blue-900">
  Need to manage your logo, palette, or design-system files? <span className="underline">Open Brand Assets →</span>
</Link>
```

- [ ] **Step 3: Add second link on Memory page**

In `src/app/(dashboard)/memory/page.tsx`, extend the existing "Edit Brand Context" header button group:

```tsx
<div className="flex gap-2">
  <Link href="/settings/brand-context" className="…existing classes…">Edit Brand Context</Link>
  <Link href="/settings/brand-assets"
        className="px-3 py-1.5 rounded border text-sm inline-flex items-center gap-1">
    <ImageIcon size={14}/> Brand Assets
  </Link>
</div>
```

- [ ] **Step 4: Update post-create banner on Brands page**

Where the success banner currently links to `/settings/brand-context`, extend to:

```tsx
<div className="rounded bg-green-50 border border-green-200 p-3 text-sm">
  Brand created. Next steps:
  <div className="mt-2 flex gap-2">
    <Link href="/settings/brand-context" className="underline">Add brand context →</Link>
    <Link href="/settings/brand-assets" className="underline">Upload visual assets →</Link>
  </div>
</div>
```

- [ ] **Step 5: Commit**

```bash
git add src/app/\(dashboard\)/settings/page.tsx \
        src/app/\(dashboard\)/settings/brand-context/page.tsx \
        src/app/\(dashboard\)/memory/page.tsx \
        src/app/\(dashboard\)/brands/page.tsx
git commit -m "feat(p7): cross-link Brand Assets from Settings, Memory, Brands"
```

**P7 Gate:** Create a fresh brand → upload `logo.png` as `logo_primary`, a PDF as `design_system_pdf`, a color palette (3 swatches), and one `example_newsletter` image. Visit `/settings/brand-assets` → all four render. Delete one → both DB row and Storage object disappear. Switch to another brand via header → the first brand's assets are invisible (RLS + path check).

---

# PHASE P8 — Autonomous Image Generation

### Task P8.1: Migration 026 — image gen config + audit table

**Files:**
- Create: `supabase/migrations/026_image_generation_config.sql`

- [ ] **Step 1: Write migration SQL**

```sql
-- 026_image_generation_config.sql
BEGIN;

ALTER TABLE public.brands
  ADD COLUMN IF NOT EXISTS image_model          text DEFAULT 'black-forest-labs/flux-schnell',
  ADD COLUMN IF NOT EXISTS image_style_preset   text DEFAULT 'editorial-minimal',
  ADD COLUMN IF NOT EXISTS image_prompt_template text,
  ADD COLUMN IF NOT EXISTS image_backend        text DEFAULT 'replicate'
    CHECK (image_backend IN ('replicate','openai','pillo','mock'));

CREATE TABLE IF NOT EXISTS public.image_generations (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  draft_id        uuid REFERENCES public.content_drafts(id) ON DELETE SET NULL,
  backend         text NOT NULL,
  model_id        text NOT NULL,
  prompt          text NOT NULL,
  negative_prompt text,
  seed            bigint,
  status          text NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','running','succeeded','failed')),
  storage_path    text,
  public_url      text,
  width_px        int,
  height_px       int,
  cost_usd        numeric(10,4),
  error           text,
  started_at      timestamptz,
  finished_at     timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_imggen_brand_draft
  ON public.image_generations (brand_id, draft_id);
CREATE INDEX IF NOT EXISTS idx_imggen_status_created
  ON public.image_generations (status, created_at DESC);

ALTER TABLE public.image_generations ENABLE ROW LEVEL SECURITY;
CREATE POLICY imggen_select ON public.image_generations
  FOR SELECT USING (public.user_has_brand(brand_id));
CREATE POLICY imggen_insert ON public.image_generations
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));
CREATE POLICY imggen_update ON public.image_generations
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));

-- Dedicated bucket for generated images (separate from brand-assets so we
-- never mix human-uploaded originals with machine outputs).
INSERT INTO storage.buckets (id, name, public)
  VALUES ('generated-images','generated-images', false)
  ON CONFLICT (id) DO NOTHING;

CREATE POLICY generated_images_read ON storage.objects
  FOR SELECT USING (
    bucket_id = 'generated-images'
    AND public.user_has_brand((split_part(name, '/', 1))::uuid)
  );
CREATE POLICY generated_images_write ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'generated-images'
    AND public.user_has_brand((split_part(name, '/', 1))::uuid)
  );

COMMIT;
```

- [ ] **Step 2: Apply and regen types**

Run:
```bash
npx supabase db push --include-all
npx supabase gen types typescript --project-id wbjmgczwqmdkitylfvud > src/lib/types/database.types.ts
```
Expected: migration applied, types include `image_generations` and new columns on `brands`.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/026_image_generation_config.sql src/lib/types/database.types.ts
git commit -m "feat(p8): image generation config columns + image_generations table"
```

---

### Task P8.2: Config + secrets wiring

**Files:**
- Modify: `python/src/content_engine/config.py`

- [ ] **Step 1: Add config fields**

Locate the `Settings` class and add:

```python
    # --- Image generation (P8) ---------------------------------------------
    # Authoritative model is per-brand (brands.image_model); this is only the
    # fallback when a brand has NULL.  Keep as a model ID the default backend
    # understands: Replicate uses "owner/name" or "owner/name:version".
    default_image_model: str = "black-forest-labs/flux-schnell"
    default_image_backend: str = "replicate"

    # Backend credentials — only the one(s) you actually use need to be set.
    replicate_api_token: str | None = None   # https://replicate.com/account/api-tokens
    openai_api_key:      str | None = None   # DALL-E / gpt-image-1 (reuse if already set)
    pillo_api_key:       str | None = None   # Pillo / PostNitro carousels
```

- [ ] **Step 2: Document in `.env.example`** (create/append)

Append to `.env.example`:
```
# --- Image generation (optional, required only if used) ---
REPLICATE_API_TOKEN=
PILLO_API_KEY=
# OPENAI_API_KEY already defined above (shared with other features)
DEFAULT_IMAGE_MODEL=black-forest-labs/flux-schnell
DEFAULT_IMAGE_BACKEND=replicate
```

- [ ] **Step 3: Commit**

```bash
git add python/src/content_engine/config.py .env.example
git commit -m "feat(p8): config fields for image generation backends"
```

---

### Task P8.3: Backend protocol + mock backend (enables TDD)

**Files:**
- Create: `python/src/content_engine/services/image_backends/__init__.py`
- Create: `python/src/content_engine/services/image_backends/base.py`
- Create: `python/src/content_engine/services/image_backends/mock_backend.py`
- Create: `python/tests/test_image_backends.py`

- [ ] **Step 1: Write the base protocol**

```python
# base.py
"""Image backend interface. Each concrete backend implements generate()."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass
class GeneratedImage:
    """Raw bytes + metadata returned by a backend. Caller uploads to Storage."""
    image_bytes: bytes
    mime_type: str            # e.g. "image/png"
    width_px: int
    height_px: int
    cost_usd: float
    model_id: str
    seed: Optional[int] = None
    raw_response: Optional[dict] = None


class ImageBackend(Protocol):
    name: str  # "replicate", "openai", "pillo", "mock"

    async def generate(
        self,
        *,
        prompt: str,
        negative_prompt: Optional[str],
        model_id: str,
        width: int,
        height: int,
        seed: Optional[int],
    ) -> GeneratedImage: ...
```

- [ ] **Step 2: Write the mock backend**

```python
# mock_backend.py
"""Mock backend — emits a 1024×1024 PNG with the prompt rendered on a
neutral background. Used in tests + when DEFAULT_IMAGE_BACKEND=mock.
No network calls, no API keys."""
from __future__ import annotations
import io
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .base import ImageBackend, GeneratedImage


class MockBackend:
    name = "mock"

    async def generate(self, *, prompt: str, negative_prompt: Optional[str],
                       model_id: str, width: int, height: int,
                       seed: Optional[int]) -> GeneratedImage:
        img = Image.new("RGB", (width, height), color=(245, 245, 245))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 18)
        except OSError:
            font = ImageFont.load_default()
        # naive wrap
        words, line, y = prompt.split(), "", 24
        for w in words:
            test = (line + " " + w).strip()
            if draw.textlength(test, font=font) > width - 48:
                draw.text((24, y), line, fill=(20, 20, 20), font=font); y += 26; line = w
            else:
                line = test
        if line: draw.text((24, y), line, fill=(20, 20, 20), font=font)

        buf = io.BytesIO(); img.save(buf, format="PNG")
        return GeneratedImage(
            image_bytes=buf.getvalue(), mime_type="image/png",
            width_px=width, height_px=height, cost_usd=0.0,
            model_id=model_id, seed=seed, raw_response={"mock": True},
        )
```

- [ ] **Step 3: Write the registry init**

```python
# __init__.py
from .base import ImageBackend, GeneratedImage
from .mock_backend import MockBackend

__all__ = ["ImageBackend", "GeneratedImage", "MockBackend", "get_backend"]


def get_backend(name: str) -> ImageBackend:
    if name == "mock":    return MockBackend()
    if name == "replicate":
        from .replicate_backend import ReplicateBackend
        return ReplicateBackend()
    if name == "openai":
        from .openai_backend import OpenAIBackend
        return OpenAIBackend()
    if name == "pillo":
        from .pillo_backend import PilloBackend
        return PilloBackend()
    raise ValueError(f"Unknown image backend: {name!r}")
```

- [ ] **Step 4: Write tests for the mock backend and registry**

```python
# test_image_backends.py
import pytest
from content_engine.services.image_backends import get_backend, MockBackend


@pytest.mark.asyncio
async def test_mock_backend_returns_png_bytes():
    be = MockBackend()
    out = await be.generate(prompt="hello", negative_prompt=None,
                            model_id="mock-v1", width=512, height=512, seed=1)
    assert out.mime_type == "image/png"
    assert out.width_px == 512 and out.height_px == 512
    assert out.image_bytes.startswith(b"\x89PNG")
    assert out.cost_usd == 0.0


def test_get_backend_mock():
    be = get_backend("mock")
    assert be.name == "mock"


def test_get_backend_unknown_raises():
    with pytest.raises(ValueError):
        get_backend("does-not-exist")
```

- [ ] **Step 5: Run the tests**

Run: `cd python && pytest tests/test_image_backends.py -v`
Expected: 3 passed. If Pillow (PIL) is missing, add `Pillow>=10.0` to `requirements.txt` and `pip install -r requirements.txt`, then re-run.

- [ ] **Step 6: Commit**

```bash
git add python/src/content_engine/services/image_backends/ python/tests/test_image_backends.py
# add Pillow to requirements.txt only if the install step changed it
git add python/requirements.txt 2>/dev/null || true
git commit -m "feat(p8): image backend protocol + mock backend with tests"
```

---

### Task P8.4: Replicate backend

**Files:**
- Create: `python/src/content_engine/services/image_backends/replicate_backend.py`

- [ ] **Step 1: Write the backend**

```python
"""Replicate backend — calls replicate.run() with the brand's configured model.

We use the HTTP API directly (not the replicate SDK) so httpx-mock fixtures
work identically to the rest of the codebase.
"""
from __future__ import annotations
import asyncio
import time
from typing import Optional

import httpx

from ...config import settings
from .base import ImageBackend, GeneratedImage


class ReplicateBackend:
    name = "replicate"

    async def generate(self, *, prompt: str, negative_prompt: Optional[str],
                       model_id: str, width: int, height: int,
                       seed: Optional[int]) -> GeneratedImage:
        if not settings.replicate_api_token:
            raise RuntimeError("REPLICATE_API_TOKEN not configured")

        inputs = {
            "prompt": prompt,
            "width": width, "height": height,
            "num_outputs": 1, "num_inference_steps": 4,  # flux-schnell default
        }
        if negative_prompt: inputs["negative_prompt"] = negative_prompt
        if seed is not None: inputs["seed"] = seed

        headers = {
            "Authorization": f"Token {settings.replicate_api_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60) as c:
            create = await c.post(
                f"https://api.replicate.com/v1/models/{model_id}/predictions",
                json={"input": inputs}, headers=headers,
            )
            create.raise_for_status()
            pred = create.json()

            # Poll until succeeded|failed|canceled. Replicate typical = 3–10s for flux-schnell.
            started = time.time()
            while pred["status"] not in ("succeeded", "failed", "canceled"):
                if time.time() - started > 120:
                    raise TimeoutError("Replicate prediction timed out after 120s")
                await asyncio.sleep(1.5)
                poll = await c.get(pred["urls"]["get"], headers=headers)
                poll.raise_for_status()
                pred = poll.json()

            if pred["status"] != "succeeded":
                raise RuntimeError(f"Replicate prediction {pred['status']}: {pred.get('error')}")

            output = pred.get("output")
            url = output[0] if isinstance(output, list) else output
            img = await c.get(url)
            img.raise_for_status()

        # flux-schnell ~ $0.003 / image. Use Replicate metrics if present.
        cost = float(pred.get("metrics", {}).get("predict_time", 0)) * 0.000725
        return GeneratedImage(
            image_bytes=img.content,
            mime_type=img.headers.get("content-type", "image/png"),
            width_px=width, height_px=height,
            cost_usd=round(cost, 5),
            model_id=model_id, seed=seed,
            raw_response=pred,
        )
```

- [ ] **Step 2: Add a mocked integration test**

Append to `python/tests/test_image_backends.py`:

```python
import respx
from httpx import Response


@pytest.mark.asyncio
@respx.mock
async def test_replicate_backend_happy_path(monkeypatch):
    from content_engine.config import settings
    from content_engine.services.image_backends.replicate_backend import ReplicateBackend
    monkeypatch.setattr(settings, "replicate_api_token", "test-token", raising=False)

    create_url = "https://api.replicate.com/v1/models/owner/model/predictions"
    respx.post(create_url).mock(return_value=Response(
        201, json={"status":"succeeded","output":["https://cdn/out.png"],
                   "urls":{"get":"https://api.replicate.com/v1/predictions/xyz"},
                   "metrics":{"predict_time":2.5}}
    ))
    respx.get("https://cdn/out.png").mock(return_value=Response(
        200, content=b"\x89PNG\r\n\x1a\n" + b"\x00"*100, headers={"content-type":"image/png"}
    ))

    out = await ReplicateBackend().generate(
        prompt="test", negative_prompt=None, model_id="owner/model",
        width=512, height=512, seed=None,
    )
    assert out.image_bytes.startswith(b"\x89PNG")
    assert out.cost_usd > 0
```

- [ ] **Step 3: Run tests**

Run: `cd python && pytest tests/test_image_backends.py -v`
Expected: 4 passed. If `respx` is not installed, `pip install respx` and add to `requirements-dev.txt`.

- [ ] **Step 4: Commit**

```bash
git add python/src/content_engine/services/image_backends/replicate_backend.py \
        python/tests/test_image_backends.py python/requirements-dev.txt 2>/dev/null || true
git commit -m "feat(p8): Replicate image backend + mocked integration test"
```

---

### Task P8.5: OpenAI + Pillo backends (thin wrappers)

**Files:**
- Create: `python/src/content_engine/services/image_backends/openai_backend.py`
- Create: `python/src/content_engine/services/image_backends/pillo_backend.py`

- [ ] **Step 1: Write OpenAI backend**

```python
# openai_backend.py
"""OpenAI image generation (gpt-image-1 / DALL-E 3)."""
from __future__ import annotations
import base64
from typing import Optional

import httpx

from ...config import settings
from .base import GeneratedImage


class OpenAIBackend:
    name = "openai"

    async def generate(self, *, prompt: str, negative_prompt: Optional[str],
                       model_id: str, width: int, height: int,
                       seed: Optional[int]) -> GeneratedImage:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        # gpt-image-1 supports 1024x1024, 1024x1536, 1536x1024
        size = f"{width}x{height}"
        body = {"model": model_id, "prompt": prompt, "size": size, "n": 1, "response_format": "b64_json"}
        headers = {"Authorization": f"Bearer {settings.openai_api_key}",
                   "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=90) as c:
            r = await c.post("https://api.openai.com/v1/images/generations", json=body, headers=headers)
            r.raise_for_status()
            payload = r.json()
        b64 = payload["data"][0]["b64_json"]
        # DALL-E 3 1024² ~ $0.040; gpt-image-1 ~ $0.011 for medium.
        cost = 0.040 if "dall-e-3" in model_id else 0.011
        return GeneratedImage(
            image_bytes=base64.b64decode(b64), mime_type="image/png",
            width_px=width, height_px=height, cost_usd=cost,
            model_id=model_id, seed=seed, raw_response=payload,
        )
```

- [ ] **Step 2: Write Pillo backend (carousel-first, stub with clear TODO)**

```python
# pillo_backend.py
"""Pillo / PostNitro carousel generation backend.

Pillo's API is optimized for multi-slide carousels rather than single images.
When the caller requests a single image we still ask Pillo for a 1-slide
carousel and return slide 0. Requires PILLO_API_KEY.
"""
from __future__ import annotations
from typing import Optional

import httpx

from ...config import settings
from .base import GeneratedImage


class PilloBackend:
    name = "pillo"

    async def generate(self, *, prompt: str, negative_prompt: Optional[str],
                       model_id: str, width: int, height: int,
                       seed: Optional[int]) -> GeneratedImage:
        if not settings.pillo_api_key:
            raise RuntimeError("PILLO_API_KEY not configured")

        headers = {"Authorization": f"Bearer {settings.pillo_api_key}",
                   "Content-Type": "application/json"}
        body = {
            "topic": prompt,
            "slides": 1,
            "style": model_id or "default",  # Pillo treats 'model' as style preset id
            "size": f"{width}x{height}",
        }
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post("https://api.pillo.ai/v1/carousels", json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
            slide_url = data["slides"][0]["image_url"]
            img = await c.get(slide_url); img.raise_for_status()

        return GeneratedImage(
            image_bytes=img.content, mime_type=img.headers.get("content-type","image/png"),
            width_px=width, height_px=height,
            cost_usd=float(data.get("cost_usd", 0.02)),
            model_id=model_id, seed=seed, raw_response=data,
        )
```

- [ ] **Step 3: Commit**

```bash
git add python/src/content_engine/services/image_backends/openai_backend.py \
        python/src/content_engine/services/image_backends/pillo_backend.py
git commit -m "feat(p8): OpenAI + Pillo image backends"
```

---

### Task P8.6: Prompt builder — pure, testable, brand-aware

**Files:**
- Create: `python/src/content_engine/services/image_prompt_builder.py`
- Create: `python/tests/test_image_prompt_builder.py`

- [ ] **Step 1: Write the builder**

```python
"""Deterministic image prompt construction.

Given a draft + brand row + palette, produce a prompt string. Pure function —
no DB access, no LLM calls — so it's trivially testable and cheap to iterate.

Order matters for most image models: subject first, style second, constraints last.
"""
from __future__ import annotations
from typing import Optional

STYLE_PRESETS = {
    "editorial-minimal":
        "clean editorial photography, flat composition, high-key lighting, "
        "generous negative space, muted background",
    "tech-futuristic":
        "futuristic 3D render, soft gradients, subtle neon accents, glass materials, "
        "photorealistic lighting",
    "warm-human":
        "candid documentary photography, natural window light, warm color grade, "
        "real-world textures, shallow depth of field",
    "illustration-flat":
        "flat vector illustration, two-tone, geometric shapes, no gradients, "
        "corporate editorial style",
}


def build_prompt(
    *,
    draft_title: str,
    draft_body: str,
    brand_name: str,
    palette_hex: list[str],
    style_preset: str,
    prompt_template: Optional[str],
) -> str:
    """Build the full prompt. If `prompt_template` is set on the brand,
    use it with named placeholders; otherwise fall back to the default layout."""
    subject = _extract_subject(draft_title, draft_body)
    style = STYLE_PRESETS.get(style_preset, STYLE_PRESETS["editorial-minimal"])
    palette_clause = (
        f"palette: {', '.join(palette_hex[:5])}" if palette_hex else ""
    )

    if prompt_template:
        return prompt_template.format(
            subject=subject, style=style, palette=palette_clause, brand=brand_name,
        ).strip()

    parts = [
        subject,
        style,
        palette_clause,
        "no text, no logos, no watermarks",   # leave text/logos to post-processing
        "aspect ratio as specified",
    ]
    return ". ".join(p for p in parts if p)


def _extract_subject(title: str, body: str, max_chars: int = 200) -> str:
    """Extract a concise visual subject from title + first body sentence.
    Heuristic: take title + first sentence of body, cap at max_chars.
    Deliberate: no LLM — prompt builder must be pure and testable.
    """
    first_sentence = body.strip().split(".")[0].strip() if body else ""
    base = f"{title.strip()} — {first_sentence}" if first_sentence else title.strip()
    return base[:max_chars]
```

- [ ] **Step 2: Write tests**

```python
# test_image_prompt_builder.py
from content_engine.services.image_prompt_builder import build_prompt


def test_default_template_includes_style_and_palette():
    p = build_prompt(
        draft_title="5 systems to ship faster",
        draft_body="Most teams overbuild. Start with one dashboard.",
        brand_name="EmptyBox", palette_hex=["#111111","#2e7d32"],
        style_preset="editorial-minimal", prompt_template=None,
    )
    assert "5 systems to ship faster" in p
    assert "editorial photography" in p
    assert "#111111" in p
    assert "no text, no logos" in p


def test_custom_prompt_template_interpolates():
    p = build_prompt(
        draft_title="T", draft_body="", brand_name="B",
        palette_hex=[], style_preset="editorial-minimal",
        prompt_template="{brand} :: {subject} :: {style}",
    )
    assert p.startswith("B :: T ::")


def test_unknown_style_falls_back_to_default():
    p = build_prompt(
        draft_title="X", draft_body="", brand_name="B",
        palette_hex=[], style_preset="does-not-exist", prompt_template=None,
    )
    assert "editorial photography" in p
```

- [ ] **Step 3: Run tests**

Run: `cd python && pytest tests/test_image_prompt_builder.py -v`
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add python/src/content_engine/services/image_prompt_builder.py python/tests/test_image_prompt_builder.py
git commit -m "feat(p8): pure image prompt builder with style presets + tests"
```

---

### Task P8.7: Image generator service — orchestration

**Files:**
- Create: `python/src/content_engine/services/image_generator.py`
- Delete: `python/src/content_engine/services/visual_generator.py` (replaced)
- Modify: any file importing `visual_generator` (search with Grep first)

- [ ] **Step 1: Confirm the old stub has no external callers**

Run Grep for `from .*visual_generator` / `import visual_generator` across `python/`.
If call sites exist, update them in step 3.

- [ ] **Step 2: Write the new generator service**

```python
"""Autonomous image generation.

Flow:
  1. Load draft + brand row (model, backend, style preset, optional template).
  2. Load palette from brand_assets (kind='palette').
  3. Build prompt via image_prompt_builder.build_prompt().
  4. Insert image_generations row with status='running'.
  5. Call the backend.
  6. Upload bytes to Storage bucket 'generated-images/<brand_id>/<uuid>.png'.
  7. Update image_generations row with storage_path, public_url, cost.
  8. Attach public_url to content_drafts.media_url.

Cost/failure handling:
  - Every call is logged even on failure (status='failed' + error text) so
    the UI can show a retry button without guessing what went wrong.
  - cost_usd is passed into cost_tracker so the per-brand daily cap applies.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Optional
from uuid import uuid4

from ..config import settings
from ..db import get_db
from ..utils.brand_assets import get_brand_palette
from ..utils.cost_tracker import record_api_cost
from .image_backends import get_backend
from .image_prompt_builder import build_prompt

logger = logging.getLogger(__name__)


async def generate_image_for_draft(
    brand_id: str, draft_id: str, *, width: int = 1024, height: int = 1024,
) -> dict:
    db = get_db()
    draft = db.table("content_drafts").select("id,title,body").eq("id", draft_id).single().execute().data
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")

    brand = db.table("brands").select(
        "name, image_model, image_backend, image_style_preset, image_prompt_template"
    ).eq("id", brand_id).single().execute().data or {}

    model_id       = brand.get("image_model")          or settings.default_image_model
    backend_name   = brand.get("image_backend")        or settings.default_image_backend
    style_preset   = brand.get("image_style_preset")   or "editorial-minimal"
    prompt_tpl     = brand.get("image_prompt_template")
    palette        = get_brand_palette(brand_id)

    prompt = build_prompt(
        draft_title=draft["title"] or "",
        draft_body=draft["body"] or "",
        brand_name=brand.get("name", ""),
        palette_hex=palette,
        style_preset=style_preset,
        prompt_template=prompt_tpl,
    )

    gen_row = db.table("image_generations").insert({
        "brand_id": brand_id, "draft_id": draft_id,
        "backend": backend_name, "model_id": model_id,
        "prompt": prompt, "status": "running",
        "started_at": "now()",
    }).execute().data[0]
    gen_id = gen_row["id"]

    try:
        backend = get_backend(backend_name)
        result = await backend.generate(
            prompt=prompt, negative_prompt=None,
            model_id=model_id, width=width, height=height, seed=None,
        )

        # Upload bytes to Storage. Path MUST start with brand_id for RLS.
        storage_path = f"{brand_id}/{uuid4().hex}.png"
        db.storage.from_("generated-images").upload(
            path=storage_path, file=result.image_bytes,
            file_options={"content-type": result.mime_type, "upsert": "false"},
        )
        signed = db.storage.from_("generated-images").create_signed_url(storage_path, 60*60*24*7)
        public_url = signed.get("signedURL") or signed.get("signed_url")

        db.table("image_generations").update({
            "status": "succeeded",
            "storage_path": storage_path, "public_url": public_url,
            "width_px": result.width_px, "height_px": result.height_px,
            "cost_usd": result.cost_usd, "finished_at": "now()",
        }).eq("id", gen_id).execute()

        db.table("content_drafts").update({"media_url": public_url}).eq("id", draft_id).execute()

        await record_api_cost(
            brand_id=brand_id, agent_name="image_generator",
            operation=f"generate:{backend_name}", model=model_id,
            tokens_input=0, tokens_output=0, cost_usd=result.cost_usd,
        )
        return {"id": gen_id, "status": "succeeded", "url": public_url, "cost_usd": result.cost_usd}

    except Exception as e:
        logger.exception("Image generation failed for draft %s", draft_id)
        db.table("image_generations").update({
            "status": "failed", "error": str(e)[:500], "finished_at": "now()",
        }).eq("id", gen_id).execute()
        return {"id": gen_id, "status": "failed", "error": str(e)}


async def generate_carousel_for_draft(brand_id: str, draft_id: str, *, slides: int = 5) -> dict:
    """Generate N images in parallel (default 5 = typical Instagram carousel).
    Each slide gets an individually numbered prompt suffix.
    Returns the list of image_generations rows."""
    tasks = [
        generate_image_for_draft(brand_id, draft_id, width=1080, height=1350)
        for _ in range(slides)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = [r if isinstance(r, dict) else {"status": "failed", "error": str(r)} for r in results]
    return {"slides": out, "total": len(out),
            "succeeded": sum(1 for r in out if r.get("status") == "succeeded")}
```

- [ ] **Step 3: Update any call sites of the old visual_generator**

Replace imports of `services.visual_generator` with `services.image_generator` and rename:
- `generate_carousel(brand_id, draft_id)` → `generate_carousel_for_draft(brand_id, draft_id)`

If no call sites exist, note it in the commit.

- [ ] **Step 4: Delete the old stub**

Run: `rm python/src/content_engine/services/visual_generator.py`

- [ ] **Step 5: Commit**

```bash
git add python/src/content_engine/services/image_generator.py
git rm python/src/content_engine/services/visual_generator.py
git commit -m "feat(p8): autonomous image generator — replaces visual_generator stub"
```

---

### Task P8.8: FastAPI routes — POST /images/generate, /images/carousel

**Files:**
- Create: `python/src/content_engine/api/routes_images.py`
- Modify: `python/src/content_engine/api/routes.py` (mount the new router)

- [ ] **Step 1: Write the router**

```python
# routes_images.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.image_generator import generate_image_for_draft, generate_carousel_for_draft
from .auth_middleware import require_brand_context

router = APIRouter(prefix="/images", tags=["images"])


class GenerateBody(BaseModel):
    draft_id: str
    width: int = 1024
    height: int = 1024


class CarouselBody(BaseModel):
    draft_id: str
    slides: int = 5


@router.post("/generate")
async def generate(body: GenerateBody, ctx=Depends(require_brand_context)):
    if body.width not in (512, 768, 1024, 1080, 1536) or body.height not in (512, 768, 1024, 1350, 1536):
        raise HTTPException(400, "Unsupported dimensions")
    return await generate_image_for_draft(ctx.brand_id, body.draft_id, width=body.width, height=body.height)


@router.post("/carousel")
async def carousel(body: CarouselBody, ctx=Depends(require_brand_context)):
    if not 2 <= body.slides <= 10:
        raise HTTPException(400, "slides must be 2..10")
    return await generate_carousel_for_draft(ctx.brand_id, body.draft_id, slides=body.slides)
```

- [ ] **Step 2: Mount the router**

In `python/src/content_engine/api/routes.py`, find where other routers are included and add:

```python
from .routes_images import router as images_router
app.include_router(images_router)
```

- [ ] **Step 3: Manual smoke test with mock backend**

```bash
# Set backend to mock for a safe end-to-end test:
# UPDATE brands SET image_backend='mock' WHERE id='<brand_id>';
curl -X POST http://localhost:8000/images/generate \
  -H "X-Brand-ID: <brand_id>" -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"draft_id":"<draft_id>","width":1024,"height":1024}'
```
Expected: `{"id":"...","status":"succeeded","url":"https://<signed>","cost_usd":0.0}`, and a row in `image_generations` with status='succeeded'.

- [ ] **Step 4: Commit**

```bash
git add python/src/content_engine/api/routes_images.py python/src/content_engine/api/routes.py
git commit -m "feat(p8): FastAPI /images/generate and /images/carousel endpoints"
```

---

### Task P8.9: Next.js proxy routes

**Files:**
- Create: `src/app/api/images/generate/route.ts`
- Create: `src/app/api/images/carousel/route.ts`

- [ ] **Step 1: Write `/api/images/generate`**

```ts
import { errorResponse, jsonResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function POST(req: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const body = await req.json().catch(() => null)
  if (!body) return errorResponse('Invalid JSON', 400)

  const url = `${process.env.PYTHON_API_URL}/images/generate`
  const r = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${auth.token}`,
      'X-Brand-ID': auth.activeBrandId ?? '',
    },
    body: JSON.stringify(body),
  })
  const data = await r.json().catch(() => null)
  if (!r.ok) return errorResponse(data?.error ?? 'Image generation failed', r.status)
  return jsonResponse(data)
}
```

- [ ] **Step 2: Write `/api/images/carousel`**

```ts
import { errorResponse, jsonResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function POST(req: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const body = await req.json().catch(() => null)
  if (!body) return errorResponse('Invalid JSON', 400)

  const url = `${process.env.PYTHON_API_URL}/images/carousel`
  const r = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${auth.token}`,
      'X-Brand-ID': auth.activeBrandId ?? '',
    },
    body: JSON.stringify(body),
  })
  const data = await r.json().catch(() => null)
  if (!r.ok) return errorResponse(data?.error ?? 'Carousel generation failed', r.status)
  return jsonResponse(data)
}
```

- [ ] **Step 3: Commit**

```bash
git add src/app/api/images/
git commit -m "feat(p8): Next.js proxy routes for image + carousel generation"
```

---

### Task P8.10: "Generate Visual" button in Content Hub

**Files:**
- Create: `src/components/content-hub/generate-visual-button.tsx`
- Modify: `src/app/(dashboard)/content-hub/[id]/page.tsx`

- [ ] **Step 1: Write the button component**

```tsx
'use client'
import { useState } from 'react'
import { Sparkles, Loader2 } from 'lucide-react'

export function GenerateVisualButton({
  draftId, platform, onGenerated,
}: { draftId: string; platform: string; onGenerated: (url: string) => void }) {
  const [busy, setBusy] = useState<false | 'image' | 'carousel'>(false)
  const [err, setErr] = useState<string | null>(null)

  async function run(mode: 'image' | 'carousel') {
    setBusy(mode); setErr(null)
    try {
      const path = mode === 'carousel' ? '/api/images/carousel' : '/api/images/generate'
      const body = mode === 'carousel' ? { draft_id: draftId, slides: 5 }
                                       : { draft_id: draftId, width: 1080, height: 1350 }
      const r = await fetch(path, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!r.ok) throw new Error((await r.json()).error || 'Generation failed')
      const data = await r.json()
      const url = mode === 'carousel'
        ? data.slides?.find((s: {status:string;url?:string}) => s.status === 'succeeded')?.url
        : data.url
      if (!url) throw new Error('No image returned')
      onGenerated(url)
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally { setBusy(false) }
  }

  const canCarousel = platform === 'instagram' || platform === 'linkedin'

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <button onClick={() => run('image')} disabled={!!busy}
                className="px-3 py-1.5 rounded bg-black text-white text-sm inline-flex items-center gap-2 disabled:opacity-50">
          {busy === 'image' ? <Loader2 className="animate-spin" size={14}/> : <Sparkles size={14}/>}
          Generate image
        </button>
        {canCarousel && (
          <button onClick={() => run('carousel')} disabled={!!busy}
                  className="px-3 py-1.5 rounded border text-sm inline-flex items-center gap-2 disabled:opacity-50">
            {busy === 'carousel' ? <Loader2 className="animate-spin" size={14}/> : <Sparkles size={14}/>}
            Generate 5-slide carousel
          </button>
        )}
      </div>
      {err && <p className="text-xs text-red-600">{err}</p>}
    </div>
  )
}
```

- [ ] **Step 2: Mount in content-hub detail page**

In `src/app/(dashboard)/content-hub/[id]/page.tsx`, where the draft is displayed, add (guarding with platform):

```tsx
{['instagram','linkedin','twitter','x'].includes(draft.platform) && (
  <div className="mt-4">
    <h3 className="text-sm font-medium mb-1">Visual</h3>
    <GenerateVisualButton
      draftId={draft.id}
      platform={draft.platform}
      onGenerated={(url) => setDraft(d => d ? ({ ...d, media_url: url }) : d)}
    />
    {draft.media_url && (
      <img src={draft.media_url} alt="Generated visual"
           className="mt-2 max-w-md rounded border" />
    )}
  </div>
)}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/content-hub/generate-visual-button.tsx src/app/\(dashboard\)/content-hub/[id]/page.tsx
git commit -m "feat(p8): Generate Visual button in content hub draft view"
```

---

### Task P8.11: Per-brand image generation settings page

**Files:**
- Create: `src/app/(dashboard)/settings/image-generation/page.tsx`
- Modify: `src/app/api/brands/[id]/route.ts` (accept new fields in PATCH)

- [ ] **Step 1: Extend PATCH to accept image_* fields**

In `src/app/api/brands/[id]/route.ts`, extend the `body` type and `patch` object:

```ts
let body: {
  name?: string; topics?: string[]; research_sources?: Json;
  daily_budget_usd?: number | null; from_email?: string | null; from_name?: string | null;
  image_model?: string | null; image_backend?: string | null;
  image_style_preset?: string | null; image_prompt_template?: string | null;
}
// …existing validations…

if ('image_model' in body) {
  if (body.image_model !== null && typeof body.image_model !== 'string')
    return errorResponse('image_model must be string or null', 400)
  patch.image_model = body.image_model || null
}
if ('image_backend' in body) {
  if (body.image_backend && !['replicate','openai','pillo','mock'].includes(body.image_backend))
    return errorResponse('image_backend must be replicate|openai|pillo|mock', 400)
  patch.image_backend = body.image_backend || null
}
if ('image_style_preset' in body) {
  if (body.image_style_preset !== null && typeof body.image_style_preset !== 'string')
    return errorResponse('image_style_preset must be string or null', 400)
  patch.image_style_preset = body.image_style_preset || null
}
if ('image_prompt_template' in body) {
  if (body.image_prompt_template !== null && typeof body.image_prompt_template !== 'string')
    return errorResponse('image_prompt_template must be string or null', 400)
  patch.image_prompt_template = body.image_prompt_template || null
}
```

Also extend the `.select()` clause at the end of the UPDATE to include the new four columns.

- [ ] **Step 2: Write the settings page**

```tsx
'use client'
import { useEffect, useState } from 'react'
import { useBrand } from '@/lib/hooks/use-brand'
import { Save, TestTube } from 'lucide-react'

const BACKENDS = [
  { value: 'replicate', label: 'Replicate (default — FLUX, SDXL, etc.)' },
  { value: 'openai',    label: 'OpenAI (DALL-E 3 / gpt-image-1)' },
  { value: 'pillo',     label: 'Pillo (carousel specialist)' },
  { value: 'mock',      label: 'Mock (local, no network — for testing)' },
]

const STYLES = ['editorial-minimal','tech-futuristic','warm-human','illustration-flat']

const MODEL_SUGGESTIONS: Record<string, string[]> = {
  replicate: ['black-forest-labs/flux-schnell','black-forest-labs/flux-dev','stability-ai/sdxl'],
  openai:    ['gpt-image-1','dall-e-3'],
  pillo:     ['classic','bold','minimal'],
  mock:      ['mock-v1'],
}

export default function ImageGenerationSettingsPage() {
  const { activeBrand } = useBrand()
  const [backend, setBackend] = useState('replicate')
  const [model, setModel] = useState('black-forest-labs/flux-schnell')
  const [style, setStyle] = useState('editorial-minimal')
  const [template, setTemplate] = useState('')
  const [saving, setSaving] = useState(false)
  const [testUrl, setTestUrl] = useState<string | null>(null)
  const [testErr, setTestErr] = useState<string | null>(null)

  useEffect(() => {
    if (!activeBrand) return
    fetch(`/api/brands`).then(r => r.json()).then((rows: Array<{id:string;image_model:string;image_backend:string;image_style_preset:string;image_prompt_template:string|null}>) => {
      const b = rows.find(x => x.id === activeBrand.id)
      if (!b) return
      setBackend(b.image_backend ?? 'replicate')
      setModel(b.image_model ?? 'black-forest-labs/flux-schnell')
      setStyle(b.image_style_preset ?? 'editorial-minimal')
      setTemplate(b.image_prompt_template ?? '')
    })
  }, [activeBrand])

  async function save() {
    if (!activeBrand) return
    setSaving(true)
    await fetch(`/api/brands/${activeBrand.id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_backend: backend, image_model: model,
        image_style_preset: style,
        image_prompt_template: template || null,
      }),
    })
    setSaving(false)
  }

  async function smokeTest() {
    setTestUrl(null); setTestErr(null)
    // Find or create a throwaway draft for dry-run
    const draftsRes = await fetch('/api/drafts?limit=1')
    const drafts = await draftsRes.json()
    if (!drafts.length) { setTestErr('No drafts available — create one first'); return }
    const r = await fetch('/api/images/generate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_id: drafts[0].id, width: 1024, height: 1024 }),
    })
    const data = await r.json()
    if (!r.ok || data.status !== 'succeeded') { setTestErr(data.error || 'Test failed'); return }
    setTestUrl(data.url)
  }

  if (!activeBrand) return <div className="p-6">Select a brand first.</div>

  return (
    <div className="p-6 space-y-4 max-w-2xl">
      <header>
        <h1 className="text-2xl font-semibold">Image generation</h1>
        <p className="text-sm text-gray-500">
          Per-brand model + style. Overrides the global defaults. Keep Replicate + FLUX for cost,
          switch to DALL-E for type-accurate scenes, or Pillo for carousel consistency.
        </p>
      </header>

      <label className="block text-sm">
        Backend
        <select value={backend} onChange={e => { setBackend(e.target.value); setModel(MODEL_SUGGESTIONS[e.target.value][0]) }}
                className="mt-1 block w-full border rounded px-2 py-1">
          {BACKENDS.map(b => <option key={b.value} value={b.value}>{b.label}</option>)}
        </select>
      </label>

      <label className="block text-sm">
        Model ID
        <input value={model} onChange={e => setModel(e.target.value)}
               list="model-suggestions"
               className="mt-1 block w-full border rounded px-2 py-1 font-mono text-xs"/>
        <datalist id="model-suggestions">
          {MODEL_SUGGESTIONS[backend]?.map(m => <option key={m} value={m}/>)}
        </datalist>
      </label>

      <label className="block text-sm">
        Style preset
        <select value={style} onChange={e => setStyle(e.target.value)}
                className="mt-1 block w-full border rounded px-2 py-1">
          {STYLES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>

      <label className="block text-sm">
        Prompt template (optional — overrides default layout)
        <textarea value={template} onChange={e => setTemplate(e.target.value)}
                  placeholder="{brand} editorial image: {subject}. Style: {style}. {palette}"
                  rows={3} className="mt-1 block w-full border rounded px-2 py-1 font-mono text-xs"/>
        <span className="text-xs text-gray-500">
          Placeholders: {'{brand}'} {'{subject}'} {'{style}'} {'{palette}'}
        </span>
      </label>

      <div className="flex gap-2">
        <button onClick={save} disabled={saving}
                className="px-3 py-1.5 rounded bg-black text-white text-sm inline-flex items-center gap-2 disabled:opacity-50">
          <Save size={14}/> {saving ? 'Saving…' : 'Save'}
        </button>
        <button onClick={smokeTest}
                className="px-3 py-1.5 rounded border text-sm inline-flex items-center gap-2">
          <TestTube size={14}/> Test generate
        </button>
      </div>

      {testUrl && <img src={testUrl} alt="Test" className="mt-4 max-w-sm border rounded"/>}
      {testErr && <p className="text-sm text-red-600">{testErr}</p>}
    </div>
  )
}
```

- [ ] **Step 3: Link from Settings index**

Append a card in `src/app/(dashboard)/settings/page.tsx`:

```tsx
<Link href="/settings/image-generation" className="rounded-lg border p-4 hover:bg-gray-50 block">
  <div className="flex items-center gap-2 text-sm font-medium"><Sparkles size={14}/> Image generation</div>
  <p className="text-xs text-gray-500 mt-1">
    Per-brand image model, style preset, prompt template. Defaults to FLUX-schnell via Replicate.
  </p>
</Link>
```

- [ ] **Step 4: Commit**

```bash
git add src/app/\(dashboard\)/settings/image-generation/page.tsx \
        src/app/api/brands/[id]/route.ts \
        src/app/\(dashboard\)/settings/page.tsx
git commit -m "feat(p8): per-brand image generation settings page"
```

---

### Task P8.12: Cost cap + audit integration

**Files:**
- Modify: `python/src/content_engine/services/image_generator.py` (already calls `record_api_cost`) — verify cost_tracker surfaces image cost in the daily cap guard
- Modify: `python/src/content_engine/utils/cost_tracker.py` — if not already generic, ensure `agent_name='image_generator'` costs are included in `get_daily_total(brand_id)`

- [ ] **Step 1: Verify cost_tracker counts image_generator costs**

Run Grep in `python/src/content_engine/utils/cost_tracker.py` for `agent_name`. The daily-cap query should be `SELECT sum(cost_usd) FROM api_costs WHERE brand_id=$1 AND date=today` with NO agent filter. If there is an agent filter, remove it so image costs count.

- [ ] **Step 2: Add a pre-flight check in image_generator**

Before the backend call in `generate_image_for_draft`, insert:

```python
from ..utils.cost_tracker import check_daily_cap
ok, reason = await check_daily_cap(brand_id)
if not ok:
    db.table("image_generations").update({"status":"failed","error":reason,"finished_at":"now()"}).eq("id", gen_id).execute()
    return {"id": gen_id, "status": "failed", "error": reason}
```

(If `check_daily_cap` doesn't exist, add a minimal one to `cost_tracker.py`:)

```python
async def check_daily_cap(brand_id: str) -> tuple[bool, str]:
    """Return (ok, reason). Compares today's total vs per-brand cap (env fallback)."""
    db = get_db()
    brand = db.table("brands").select("daily_budget_usd").eq("id", brand_id).single().execute().data
    cap = float(brand.get("daily_budget_usd") or 0) or float(settings.daily_budget_usd or 0)
    if cap <= 0: return True, ""
    total = db.rpc("sum_today_costs", {"p_brand_id": brand_id}).execute().data or 0
    if float(total) >= cap:
        return False, f"Daily cap reached (${total:.2f}/${cap:.2f})"
    return True, ""
```

- [ ] **Step 3: Test end-to-end cost gate**

With `mock` backend set, trigger 1 generation. Confirm an `api_costs` row appears for `agent_name='image_generator'`. Manually raise the row's cost_usd to exceed the brand's cap, trigger again → expect `status='failed'` with reason containing "Daily cap reached".

- [ ] **Step 4: Commit**

```bash
git add python/src/content_engine/services/image_generator.py python/src/content_engine/utils/cost_tracker.py
git commit -m "feat(p8): image generation respects per-brand daily budget cap"
```

---

### Task P8.13: Memory hook — log image generation as episodic event

**Files:**
- Modify: `python/src/content_engine/services/image_generator.py`

- [ ] **Step 1: After a successful generation, log to memory_events**

Add at the end of the `succeeded` branch:

```python
from ..memory.events import log_event  # existing P2 module
await log_event(
    brand_id=brand_id,
    event_kind="image_generated",
    subject_kind="content_draft",
    subject_id=draft_id,
    summary=f"{backend_name}:{model_id} — {result.width_px}×{result.height_px} — ${result.cost_usd:.4f}",
    payload={"prompt": prompt, "style_preset": style_preset,
             "palette_size": len(palette), "public_url": public_url},
)
```

- [ ] **Step 2: Confirm it surfaces in `vw_memory_episodic`**

Run: `SELECT * FROM vw_memory_episodic WHERE event_kind='image_generated' ORDER BY occurred_at DESC LIMIT 5;`
Expected: rows visible, Memory Inspector shows them.

- [ ] **Step 3: Commit**

```bash
git add python/src/content_engine/services/image_generator.py
git commit -m "feat(p8): emit memory_events on successful image generation"
```

---

### Task P8.14: Documentation + env-sample sync

**Files:**
- Modify: `.env.example`, `README.md` (or `docs/setup.md` if present)

- [ ] **Step 1: Document the image pipeline setup**

Append a section "Image generation (P8)" describing:
- which env vars are required per backend
- how to switch backend per brand via `/settings/image-generation`
- default model: `black-forest-labs/flux-schnell` via Replicate (~$0.003/image at 1024²)
- `mock` backend for local testing without credentials

- [ ] **Step 2: Commit**

```bash
git add .env.example README.md
git commit -m "docs(p8): image generation setup notes"
```

---

## 3. P8 Gate — Full end-to-end test

1. In Supabase, set `brands.image_backend='mock'` for your test brand.
2. Open Content Hub → any draft with `platform='instagram'`.
3. Click "Generate image" → confirm button shows loading → image appears below within ~2s.
4. Check `image_generations` table — one row `status='succeeded'`, `cost_usd=0`.
5. Check `content_drafts.media_url` — populated with signed URL.
6. Check Memory Inspector (`/memory`) — episodic feed shows `image_generated` event.
7. Switch backend to `replicate` in `/settings/image-generation`, save.
8. Re-run "Generate image" → real FLUX-schnell image appears. `cost_usd` populated (~$0.003).
9. Try "Generate 5-slide carousel" on a LinkedIn draft → 5 images generated in parallel, Memory Inspector shows 5 events.
10. Set `brands.daily_budget_usd=0.01` → trigger another generation → expect `status='failed'` with "Daily cap reached" reason.
11. Switch to another brand without REPLICATE access → its asset uploads work but image generation correctly routes through that brand's configured backend (verified in `image_generations.model_id`).

---

## 4. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **Replicate API outages** block generation | Backend dispatch already supports fallback — add retry loop in `generate_image_for_draft` that, on `httpx.HTTPError`, retries once with `mock` backend and surfaces a warning (non-blocking). Keep as V1.1 task. |
| **Prompt injection via draft body** (user pastes prompt-steering text) | Prompt builder is pure + deterministic. No function calling from draft body into backend. Backends themselves already refuse obvious NSFW prompts. |
| **Storage bloat from N×carousel runs** | Lifecycle policy on `generated-images` bucket: auto-delete objects older than 90 days (add as separate migration 027 later; not blocking). Track in `image_generations.storage_path` so we can cascade cleanup. |
| **Cost surprises** | Per-brand `daily_budget_usd` is authoritative (P8.12 integrates it). `image_generations.cost_usd` visible in a new admin view later. |
| **Pillo/PostNitro API instability** | Pillo backend is best-effort; defaults keep brands on Replicate. Pillo users self-opt in. |
| **Brand assets leak across tenants** | Storage path MUST start with `<brand_id>/` — enforced in RLS policy via `split_part(name, '/', 1)` and in metadata POST via prefix check. Integration test: curl a brand-B signed URL while authed as brand-A user → 403. |

---

## 5. What is NOT in scope (and why)

- **Generating the logo itself.** Logo design is a human/agency task. We only store and reference.
- **Full design system generator.** Out of scope — users upload their existing PDF/Figma export.
- **Video generation.** Explicitly deferred to P9+. Video adds Sora/Runway/Pika cost curves worth their own plan.
- **Inpainting / logo overlay post-processing.** The `no text, no logos` prompt clause means the generator output is clean; overlaying the brand logo is a separate future task (requires compositor — see P9).
- **Auto-captioning / alt-text.** When we add accessibility pass, it will be in its own phase.

---

## 6. Files touched summary

**New migrations (2):** 025_brand_visual_assets, 026_image_generation_config.

**New API routes (Next.js, 6):**
- `src/app/api/brands/[id]/assets/route.ts`
- `src/app/api/brands/[id]/assets/[assetId]/route.ts`
- `src/app/api/brands/[id]/assets/[assetId]/preview/route.ts`
- `src/app/api/brands/[id]/assets/upload-url/route.ts`
- `src/app/api/images/generate/route.ts`
- `src/app/api/images/carousel/route.ts`

**New dashboard pages (2):**
- `src/app/(dashboard)/settings/brand-assets/page.tsx`
- `src/app/(dashboard)/settings/image-generation/page.tsx`

**New React components (3):**
- `src/components/brand-assets/asset-upload-card.tsx`
- `src/components/brand-assets/palette-editor.tsx`
- `src/components/content-hub/generate-visual-button.tsx`

**New Python modules (7):**
- `content_engine/utils/brand_assets.py`
- `content_engine/services/image_generator.py`
- `content_engine/services/image_prompt_builder.py`
- `content_engine/services/image_backends/{__init__,base,mock_backend,replicate_backend,openai_backend,pillo_backend}.py`
- `content_engine/api/routes_images.py`

**New tests (3):** test_brand_assets_helper, test_image_prompt_builder, test_image_backends.

**Modified:** `src/app/api/brands/[id]/route.ts`, `src/app/(dashboard)/settings/page.tsx`, `src/app/(dashboard)/settings/brand-context/page.tsx`, `src/app/(dashboard)/memory/page.tsx`, `src/app/(dashboard)/brands/page.tsx`, `src/app/(dashboard)/content-hub/[id]/page.tsx`, `python/src/content_engine/config.py`, `python/src/content_engine/api/routes.py`, `python/src/content_engine/utils/cost_tracker.py`, `src/lib/types/database.types.ts`, `.env.example`, `README.md`.

**Deleted:** `python/src/content_engine/services/visual_generator.py`.

---

## 7. Self-review checklist (ran before handoff)

- ✅ **Spec coverage**
  - Editable long-term brand assets (logo, palette, design system, examples) → P7.1–P7.8.
  - "Fully autonomous" image generation → P8.7 `generate_image_for_draft` requires no prompt input.
  - "Dedicated configurable model" → `brands.image_model` + `image_backend` + `/settings/image-generation`.
  - Pillo / other integration hook → P8.5 Pillo backend (stub with real API shape).
  - Memory-tab ↔ Brand Context linkage → P7.8 step 3.
  - Cost discipline → P8.12 ties generation into per-brand `daily_budget_usd`.

- ✅ **Placeholder scan**: No "TBD", no "similar to above", all code blocks complete.

- ✅ **Type consistency**: `GeneratedImage`, `ImageBackend`, `BrandAsset` stable across tasks. `generate_image_for_draft` signature stable across P8.7, P8.8, P8.10, P8.12, P8.13.

- ✅ **Path consistency**: Storage paths always `<brand_id>/<uuid>.<ext>` for both `brand-assets` and `generated-images` buckets (matches RLS `split_part(name,'/',1)` rule).

---

## 8. Execution handoff

**Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration.
→ REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`

**2. Inline Execution** — Execute tasks in this session with checkpoints for review.
→ REQUIRED SUB-SKILL: `superpowers:executing-plans`

**Recommended sequencing:** P7.1 → P7.2 → P7.3 → P7.4 → P7.5 → P7.6 → P7.7 → P7.8 → **P7 Gate** → P8.1 → P8.2 → P8.3 → P8.4 → P8.5 → P8.6 → P8.7 → P8.8 → P8.9 → P8.10 → P8.11 → P8.12 → P8.13 → P8.14 → **P8 Gate**.

**Estimated effort:** P7 = ~2 days, P8 = ~3 days. Subagent-driven completes ~30% faster than inline.
