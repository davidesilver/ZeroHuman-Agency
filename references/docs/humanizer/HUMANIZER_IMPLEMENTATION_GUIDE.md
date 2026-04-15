# Humanizer Implementation Guide

## Overview

The Humanizer Agent removes AI-generated writing patterns and applies brand voice calibration using the blader/humanizer skill (29 anti-AI patterns from Wikipedia's "Signs of AI writing").

**Position in pipeline:** After `god_system.run_god_mode()`, before `adapter.adapt_for_platforms()`

**Cost estimation:** ~$0.002-0.004 per draft (free model) or ~$0.005-0.008 (Haiku)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTENT PIPELINE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. writer.generate_draft()                                  │
│     └─> Creates raw draft from research                     │
│                                                             │
│  2. god_system.run_god_mode()                               │
│     └─> Advocates, Fact-checks, Creative, Synthesis          │
│     └─> Status: "approved" or "in_review"                    │
│                                                             │
│  3. 👉 humanizer.humanize_draft()  [NEW!]                   │
│     ├─> PASS 1: 29 AI patterns + voice calibration           │
│     ├─> PASS 2: Anti-AI audit "What's still AI?"            │
│     └─> Status: "humanized"                                  │
│                                                             │
│  4. adapter.adapt_for_platforms()                           │
│     └─> Adapts for LinkedIn, X, Instagram, etc.              │
│                                                             │
│  5. publisher.publish_draft()                                │
│     └─> Posts to platforms                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Database Changes

Run migration `010_humanizer_control.sql`:

```bash
supabase db push
```

This adds:
- `brands.use_humanizer` (BOOLEAN) - Enable/disable per brand
- `brands.humanizer_channels` (TEXT[]) - Platforms to apply humanization
- `brands.humanizer_model_override` (TEXT) - Optional explicit model
- `humanizer_performance` table - Feedback loop tracking

## Integration: Orchestrator

File: `python/src/content_engine/orchestrator/workflow.py` (or similar)

```python
from ..agents.humanizer import humanize_draft

async def process_draft(brand_id: str, draft_id: str) -> dict:
    """Main content processing pipeline."""

    # 1. Write draft
    draft = await generate_draft(brand_id, research_item_id)

    # 2. GOD Mode review
    god_result = await run_god_mode(brand_id, draft["draft"]["id"])

    # 3. Humanize (NEW!)
    if god_result["verdict"] == "pass":  # Only humanize approved content
        await _run_humanizer_if_enabled(brand_id, draft["draft"]["id"])

    # 4. Adapt for platforms
    adapted = await adapt_for_platforms(brand_id, draft["draft"]["id"])

    # 5. Publish
    published = await publish_draft(brand_id, draft["draft"]["id"])

    return published


async def _run_humanizer_if_enabled(brand_id: str, draft_id: str) -> dict:
    """Run humanizer if enabled for this brand and platform."""
    db = get_db()

    # Get brand settings
    brand = db.table("brands").select("*").eq("id", brand_id).single().execute()
    brand_data = brand.data

    # Check if humanizer is enabled
    if not brand_data.get("use_humanizer", False):
        logger.info("Humanizer disabled for brand %s, skipping", brand_id)
        return {"status": "skipped", "reason": "disabled"}

    # Get draft platform
    draft = db.table("content_drafts").select("*").eq("id", draft_id).single().execute()
    draft_platform = draft.data.get("platform", "")

    # Check if platform is in enabled channels
    enabled_channels = brand_data.get("humanizer_channels", ["linkedin", "blog"])
    if draft_platform not in enabled_channels:
        logger.info("Humanizer not enabled for platform %s, skipping", draft_platform)
        return {"status": "skipped", "reason": "platform_not_enabled"}

    # Run humanizer
    model_override = brand_data.get("humanizer_model_override")
    result = await humanize_draft(
        brand_id=brand_id,
        draft_id=draft_id,
        model_override=model_override,
    )

    return result
```

## Voice Calibration

Voice calibration uses a priority system:

1. **Manual gold_examples** (highest priority) - Set in `brands.tone_of_voice.gold_examples`:
   ```json
   {
     "gold_examples": [
       {
         "title": "Best performing post about X",
         "content": "This is the content...",
         "notes": "Why this works well for our brand..."
       }
     ]
   }
   ```

2. **Automatic top performers** (fallback) - Top-3 by `engagement_score` from `content_performance`

3. **Default natural voice** (fallback) - Varied rhythm, opinions, first-person perspective

### Setting Manual Gold Examples

Via Supabase Dashboard or API:

```sql
UPDATE brands
SET tone_of_voice = jsonb_set(
  tone_of_voice,
  '{gold_examples}',
  '[
    {"title": "Example 1", "content": "Your best content..."},
    {"title": "Example 2", "content": "Another great example..."}
  ]'::jsonb
)
WHERE id = 'your-brand-id';
```

## Model Control

### Default Routing (Recommended)

Uses capability-based routing:
- Primary: `google/gemma-4-150b:free` (FREE)
- Fallback: `anthropic/claude-3-5-haiku-20241022`

### Explicit Model Override (Optional)

Set `brands.humanizer_model_override` to force a specific model:

```sql
UPDATE brands
SET humanizer_model_override = 'anthropic/claude-3-5-haiku-20241022'
WHERE id = 'your-brand-id';
```

Available models:
- `google/gemma-4-150b:free` - Free, good quality
- `anthropic/claude-3-5-haiku-20241022` - Best quality, low cost
- `anthropic/claude-3-5-sonnet-20241022` - Best quality, higher cost

## Feedback Loop

Track if humanization improves performance:

```python
def track_humanizer_effectiveness(draft_id: str, engagement_metrics: dict):
    """Call this after getting engagement data (e.g., from Postiz)."""
    db = get_db()

    # Get draft and humanizer metadata
    draft = db.table("content_drafts").select("*").eq("id", draft_id).single().execute()

    # Check if this was humanized
    if draft.data.get("status") != "humanized":
        return

    # Store for analysis
    db.table("humanizer_performance").insert({
        "draft_id": draft_id,
        "brand_id": draft.data["brand_id"],
        "ai_patterns_found": 0,  # Extract from humanizer_result if available
        "remaining_ai_tells": 0,
        "engagement_score": engagement_metrics.get("score", 0),
        "platform": draft.data.get("platform", ""),
        "model_used": engagement_metrics.get("model_used", ""),
    }).execute()
```

### Analysis Queries

```sql
-- Do humanized posts perform better?
SELECT
    AVG(engagement_score) as avg_score,
    COUNT(*) as post_count
FROM humanizer_performance
GROUP BY (ai_patterns_found > 5);

-- Which platforms benefit most?
SELECT
    platform,
    AVG(engagement_score) as avg_engagement,
    COUNT(*) as post_count
FROM humanizer_performance
WHERE engagement_score IS NOT NULL
GROUP BY platform
ORDER BY avg_engagement DESC;
```

## Testing

```bash
# Run tests
cd python
python -m pytest tests/test_humanizer.py -v

# Run specific test
python -m pytest tests/test_humanizer.py::TestVoiceCalibration::test_manual_gold_examples_priority -v
```

## Monitoring

Metrics are automatically tracked via the cost tracking system:
- Context: `humanizer_pass1` and `humanizer_pass2`
- Action: `initial_humanization` and `anti_ai_audit`
- Model: Tracked in `cost_tracking` table

## Rollback Plan

If humanization causes issues:

### 1. Disable Instantly
```sql
UPDATE brands SET use_humanizer = FALSE WHERE id = 'your-brand-id';
```

### 2. Revert Drafts
```sql
-- Revert to previous version (if versioning is implemented)
UPDATE content_drafts
SET body = (
  SELECT body FROM content_drafts_versions
  WHERE draft_id = content_drafts.id
  ORDER BY version DESC
  LIMIT 1 OFFSET 1
)
WHERE status = 'humanized';
```

### 3. Delete or Disable Agent
```python
# In orchestrator/workflow.py, comment out the humanizer call
# await _run_humanizer_if_enabled(brand_id, draft["draft"]["id"])
```

## Troubleshooting

### Humanizer fails but draft continues
**Symptom:** Pass 2 fails, but Pass 1 result is used
**Solution:** This is expected behavior. Check logs for why Pass 2 failed.

### Voice calibration not working
**Symptom:** Default voice is used instead of brand examples
**Solution:** Check `brands.tone_of_voice.gold_examples` structure. Verify `content_performance` has data if using automatic fallback.

### Cost higher than expected
**Symptom:** Costs are 5-10x estimates
**Solution:** Check `brands.humanizer_model_override` - it might be set to a more expensive model. Default should use free model.

### Italian text not properly humanized
**Symptom:** AI patterns still visible in Italian
**Solution:** The 29 patterns are English-based. The prompt instructs the model to adapt to Italian, but you may need to add Italian-specific patterns to `humanizer_skill.md`.

## Frontend Integration

See `FRONTEND_INTEGRATION.md` for UI/UX changes needed:
- Brand settings page: Add humanizer controls
- Draft detail page: Show humanization status
- Analytics dashboard: Humanizer performance metrics
