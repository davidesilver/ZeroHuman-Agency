# Scoring Rubric Design Guide

## Philosophy

The scoring agent's job is not to predict virality — it is to predict whether a piece of content will be **valuable to your specific audience on your specific channels today**. These are different problems.

A score of 80+ means: "This is worth the cost of writing and the reputational cost of publishing." Not: "This will get 10,000 impressions."

## Designing Your Rubric

### Step 1: Define your audience precisely

Before setting weights, write one sentence that describes exactly who your content is for:

> "Our audience is [job title] at [company type] who care about [primary concern] and make decisions about [domain]."

This sentence is the lens for every dimension weight.

### Step 2: Set dimension weights

The five dimensions are fixed. Their weights are yours to set.

| Dimension | What it measures | When to weight high |
|-----------|-----------------|---------------------|
| Relevance | Topic match to your vertical | Always ≥ 0.30 |
| Novelty | How new is this information? | Media/content verticals |
| Trend Signal | Is interest in this topic growing? | B2C, media |
| Audience Fit | Does your ICP actually care? | B2B, niche verticals |
| Risk | Factual/reputational/legal exposure | Regulated industries |

### Step 3: Set thresholds

```
auto_approve ≥ 75    (proven items: write and publish)
review_queue  50-74  (borderline: human decides)
discard      < 50    (archive: never processed)
```

Start conservative. Lower `auto_approve` only after you have 30+ days of engagement data showing the system's judgment is reliable.

### Step 4: Define auto-discard rules

Items that should never reach scoring, regardless of apparent relevance:

```yaml
auto_discard:
  older_than_days: 7           # No stale content
  contains_phrases:
    - "press release"
    - "sponsored content"
    - "advertisement"
  source_domain_blacklist:
    - "spammy-pr-site.com"
  min_content_length: 150      # Ignore stub articles
```

## Rubric Examples by Vertical

### Media Company (AI/Tech)
```yaml
relevance:    0.30
novelty:      0.30
trend_signal: 0.25
audience_fit: 0.10
risk:         0.05
auto_approve: 72
```

### B2B SaaS Intelligence
```yaml
relevance:    0.40
novelty:      0.20
trend_signal: 0.20
audience_fit: 0.15
risk:         0.05
auto_approve: 78
```

### Industrial / Regulated Industry
```yaml
relevance:    0.45
risk:         0.25
novelty:      0.15
trend_signal: 0.10
audience_fit: 0.05
auto_approve: 80
```
