# Plan: P8 — Image Generation Hardening

> Source PRD: `plans/visual-assets-and-image-generation-plan.md`

## Architectural decisions

- **Routes**: FastAPI image routes mounted under `/images/*` in `main.py`; Next.js proxy routes 1:1 under `/api/images/*`
- **Schema**: `image_generations` is the audit & job-status source-of-truth; `content_drafts.media_url` is `text[]` (append-only for new media)
- **Key models**: `ImageBackend` protocol with `MockBackend`, `ReplicateBackend`, `OpenAIBackend`, `PilloBackend`; `ImageGenerator` orchestrator
- **Cost tracking**: `track_cost()` MUST accept optional `cost_usd` override for non-LLM services (images, external APIs)
- **Async pattern**: Jobs run as `asyncio.create_task` with polling status via `GET /images/jobs/{job_id}`; client polls every 2s
- **Media storage**: Supabase Storage bucket `generated-images` with RLS scoped by `split_part(name, '/', 1)::uuid`
- **Backend default**: `mock` for zero-cost dev; `replicate` / `openai` for staging & production

---

## Phase 1: "Generate Image" End-to-End Fix

**User stories**: Configure backend, generate mock image, see preview

### What to build
Repair the complete end-to-end flow from button click in the UI to generated image preview. Fix every blocking bug so the tracer bullet works.

### Acceptance criteria
- [ ] `routes_images.py` mounted in `main.py` with prefix `/images`
- [ ] `config.py` expanded with `ImageSettings`: `replicate_api_token`, `openai_api_key`, `pillo_api_key`, `default_image_backend`, `default_image_model`
- [ ] `.env.example` updated with all new image generation env vars
- [ ] `PATCH /api/brands/[id]` accepts `image_backend`, `image_model`, `image_style_preset`, `image_prompt_template`
- [ ] `track_cost()` accepts optional `cost_usd` parameter (fixes runtime TypeError on successful generation)
- [ ] `image_generator.py` appends new media URL to `content_drafts.media_url` array (`.rpc('array_append', ...)`) instead of overwriting with a string
- [ ] `GenerateVisualButton` integrated into `DraftCard` quick-actions menu in `content-hub/page.tsx`
- [ ] `Pillow` added to `pyproject.toml` dependencies (mock backend requires PIL)
- [ ] Manual E2E test: click Generate → `pending` → `succeeded` → image URL visible in UI
- [ ] Old `visual_generator.py` stub deleted

---

## Phase 2: Async Job Queue

**User stories**: Generate with Replicate without Vercel timeout, track progress, automatic retry

### What to build
Isolate slow backend latency (Replicate can take 10–30s) from the synchronous request/response cycle. Implement client-side polling with resilient job execution.

### Acceptance criteria
- [ ] `POST /images/generate` returns immediately `{job_id, status: pending}` instead of waiting for backend completion
- [ ] `image_generator.py` executes generation in `asyncio.create_task` with exception handling and status updates
- [ ] New route `GET /images/jobs/{job_id}` for polling job status (`pending|running|succeeded|failed`)
- [ ] Next.js proxy route `/api/images/jobs/[id]/route.ts`
- [ ] `GenerateVisualButton` shows progress indicator with polling every 2s until terminal state
- [ ] Automatic retry on failure: max 3 attempts with exponential backoff, tracked in `image_generations.metadata`
- [ ] Job timeout: after 5 minutes mark `failed` with error `"timeout"`
- [ ] `generate_carousel_for_draft()` also uses async job pattern with batch status tracking

---

## Phase 3: Draft Detail & Media Gallery

**User stories**: Open a draft, view generated images, regenerate, delete media

### What to build
Create the missing detail page and a mini-CMS for draft-attached media.

### Acceptance criteria
- [ ] `src/app/(dashboard)/content-hub/[id]/page.tsx` — layout with title, body, metadata, media section
- [ ] Media gallery component showing `media_url[]` as image grid with signed-URL previews
- [ ] "Regenerate image" button in detail calling `/api/images/generate` with `draft_id`
- [ ] "Delete media" button removes URL from `media_url` array and deletes from Storage
- [ ] `content-hub/page.tsx` updated so `DraftCard` click navigates to detail
- [ ] Draft detail includes `GenerateVisualButton` with platform-aware defaults

---

## Phase 4: Cost Control & Observability

**User stories**: Understand spend, stay within budget, have image generation logs

### What to build
Close the cost tracking loop and add operational visibility.

### Acceptance criteria
- [ ] Database index on `image_generations(brand_id, created_at)` for fast daily aggregation queries
- [ ] Settings sub-section in `/settings/image-generation`: generations/day count, total cost, recent jobs list
- [ ] `check_daily_cost_cap` correctly includes image generation costs in daily sum
- [ ] UI alert when daily cap reaches 80%
- [ ] `image_generations` table queryable via API with filters (`status`, `date_from`, `date_to`)
- [ ] Python test suite updated: mock async job lifecycle, test retry logic, test `cost_usd` override path
- [ ] Documentation updated: `docs/IMAGE_GENERATION.md` with architecture, env vars, backend comparison

---

## Phase 5: Backend Hardening & Production Readiness

**User stories**: Use real backends safely, handle errors gracefully, scale if needed

### What to build
Polish real backends and ensure robust production behavior.

### Acceptance criteria
- [ ] `ReplicateBackend`: validate webhook/polling hybrid if Replicate supports it; otherwise keep polling with timeout
- [ ] `OpenAIBackend`: handle `b64_json` response correctly, validate dimension constraints per model
- [ ] `PilloBackend`: implement real HTTP call or decide to deprecate if API unstable
- [ ] Global rate limiter per backend (e.g., max 5 concurrent Replicate jobs)
- [ ] Circuit breaker pattern: if a backend fails 5 times in 10 minutes, fallback to `mock` with alert
- [ ] All image routes protected by `JWTAuthMiddleware` with proper `brand_id` scoping
- [ ] Final regression test: mock → Replicate → OpenAI backend switch works without code changes
