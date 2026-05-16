# ViMax Microservice — HITL Decision Gate

**Status**: BLOCKED — awaiting human decision

**GitHub issue**: #17 — Phase 15

## What needs a decision

Before implementing the ViMax full-pipeline video microservice, the following must be decided and documented:

### 1. Budget approval

ViMax calls AI video generation APIs per-render. Estimated costs:

| Provider | ~Cost/minute | Quality |
|----------|-------------|---------|
| Veo 3 (Google) | ~$0.35/min | Highest |
| Kling (Kuaishou) | ~$0.12/min | High |
| Higgsfield | ~$0.08/min | Medium |
| Pixelle | ~$0.06/min | Medium |

**Decision needed**: monthly budget cap per brand + global cap.

### 2. Backend provider selection

- **Veo 3**: Best quality, highest cost, requires Google AI Studio access
- **Kling**: Strong quality/cost ratio, REST API available
- **Higgsfield**: Good for talking-head + scene transitions
- **Pixelle**: Most affordable, open-source-friendly

**Decision needed**: primary provider + fallback.

### 3. Pipeline scope

ViMax v1 could be:
- **Narrow**: brief → script → clip (3 steps, simpler)
- **Full**: brief → script → storyboard → individual clips → composite → MP4 (6 steps, higher quality)

**Decision needed**: which pipeline scope for v1.

## How to unblock

1. Fill in the decisions above
2. Update this doc with the approved choices
3. Remove the BLOCKED status
4. Implementation can proceed per the acceptance criteria in `docs/plans/capability-expansion.md`

## Pre-built infrastructure

The following are already in place (ready for ViMax):
- `videos` table extended with `kind` column — add `'vimax'` to the CHECK constraint
- `heygen_usage` quota pattern can be replicated for ViMax
- `/api/video/generate` endpoint structure is ready for `kind="full-pipeline"`
- Feature flag infra: `BRAND_SECRETS_ENCRYPTION_KEY` + `feature_flags` table
