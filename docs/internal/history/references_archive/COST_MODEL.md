# API Cost Model

## Estimation Formula

```
daily_cost = (
    items_collected × cost_per_prefilter_call +
    items_passing_prefilter × cost_per_score_call +
    items_approved × cost_per_write_call +
    items_in_god_mode × cost_per_god_call × 4
)
```

## Model Cost Reference (April 2026, via OpenRouter)

| Model | Input $/1M tokens | Output $/1M tokens | Best for |
|-------|-------------------|-------------------|---------|
| Claude Haiku 3 | $0.25 | $1.25 | Pre-filter |
| Claude Sonnet 4.5 | $3.00 | $15.00 | Scoring, writing |
| Claude Opus 4 | $15.00 | $75.00 | GOD Mode only |
| Gemini Flash 2.0 | $0.10 | $0.40 | Budget pre-filter |
| GPT-4o mini | $0.15 | $0.60 | Budget pre-filter |

## Single Brand, Daily Pipeline

| Stage | Model | Items | Avg tokens | Cost/day |
|-------|-------|-------|-----------|----------|
| Pre-filter | Haiku | 500 | 300 in + 50 out | ~$0.40 |
| Scoring | Sonnet | 150 | 800 in + 150 out | ~$1.80 |
| Writing | Sonnet | 10 | 1200 in + 600 out | ~$0.60 |
| GOD Mode | Opus | 3 × 4 sub-agents | 2000 in + 800 out | ~$0.80 |
| **Total** | | | | **~$3.60/day** |

Monthly: ~$108/month per brand.

## Optimization Strategies

1. **Two-stage pre-filter:** Use a $0.10/1M model (Gemini Flash) for the first pass. Only items that clearly match your vertical proceed to Sonnet scoring.

2. **GOD Mode gating:** Every point you raise the GOD Mode threshold reduces cost significantly. At threshold 85, you might run GOD Mode on 1 item/day instead of 5 — saving ~$2/day.

3. **Daily publish cap:** Set `daily_publish_limit: 3`. Even if 10 items score above threshold, only 3 go through the full writing pipeline. Queue the rest for tomorrow.

4. **Writing model downgrade:** If your content is conversational (LinkedIn posts, newsletters), Sonnet produces near-identical quality to Opus at 1/5th the cost. Reserve Opus only for GOD Mode synthesis.

5. **Source quality over quantity:** 50 high-quality RSS feeds produce better signal than 500 low-quality ones — at the same pre-filter cost. Invest time in curating sources rather than adding volume.

## Multi-Brand Scaling

| Brands | Daily cost | Monthly cost |
|--------|-----------|-------------|
| 1 | ~$3.60 | ~$108 |
| 3 | ~$10.80 | ~$324 |
| 5 | ~$18.00 | ~$540 |
| 10 | ~$36.00 | ~$1,080 |

At 10 brands, a shared pre-filter that processes all brands' sources in a single pass can reduce total cost by ~30%.
