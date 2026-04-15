# Using Your Claude Subscription in Content Engine

## Overview

You can use your Claude Pro/Team subscription to power the Content Engine instead of (or in addition to) OpenRouter free models.

## Two Ways to Use Claude

### 1. **Via Anthropic API Direct** (Recommended for Subscription)

**Uses your Claude subscription credits ✅**

```bash
# In your .env file
ANTHROPIC_API_KEY=sk-ant-your-key-from-console.anthropic.com
USE_CLAUDE_SUBSCRIPTION=true
```

**Benefits:**
- Uses your Claude subscription credits
- Direct API access to Anthropic
- No OpenRouter dependency
- Better for production use

**Cost:**
- Charged to your Claude subscription
- Haiku: $0.00025/1K input, $0.00125/1K output
- Sonnet: $0.003/1K input, $0.015/1K output

### 2. **Via OpenRouter**

**Does NOT use your Claude subscription credits ❌**

```bash
# In your .env file
OPENROUTER_API_KEY=your-openrouter-key
USE_CLAUDE_SUBSCRIPTION=false  # Default
```

**Benefits:**
- Access to many models from one API
- Free tier available
- Easy to switch between providers

**Cost:**
- Charged to your OpenRouter account
- Separate billing from Claude subscription

## Configuration

### Enable Claude Subscription

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxx
USE_CLAUDE_SUBSCRIPTION=true
```

### Model Selection by Task Type

When `USE_CLAUDE_SUBSCRIPTION=true`:

| Task Type | Model Used | Why |
|-----------|------------|-----|
| `reasoning` | Claude Sonnet | Complex reasoning required |
| `agentic` | Claude Sonnet | Multi-step agent work |
| `coding` | Claude Sonnet | Code generation and analysis |
| `creative` | Claude Haiku | Content creation (faster, cheaper) |
| `language` | Claude Haiku | Text processing |
| `knowledge` | Claude Haiku | Information retrieval |

When `USE_CLAUDE_SUBSCRIPTION=false` (default):

| Task Type | Primary Model | Fallback |
|-----------|--------------|----------|
| `reasoning` | Xiaomi MiMo (Free) | o3-mini |
| `creative` | Gemma 4 (Free) | Claude Haiku |
| `knowledge` | Arcee Trinity (Free) | Gemini 2.5 Flash |
| `agentic` | Zhipu GLM 5.5 (Free) | Claude Sonnet |
| `coding` | Qwen 3.5 Max (Free) | Mistral Devstral 2 |

## Getting Your Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign in with your Claude account
3. Navigate to API Keys
4. Create a new API key
5. Add it to your `.env` file

**Note:** If you have Claude Pro/Team, you get monthly API credits. Check your dashboard for available credits.

## Cost Comparison

### Example: 100 Content Drafts

| Method | Model | Input Tokens | Output Tokens | Cost |
|--------|-------|--------------|---------------|------|
| **Claude Subscription** | Haiku | 50,000 | 150,000 | $0.20 |
| **Claude Subscription** | Sonnet | 50,000 | 150,000 | $2.40 |
| **OpenRouter Free** | Gemma 4 | 50,000 | 150,000 | $0.00 |
| **OpenRouter Paid** | Claude Haiku | 50,000 | 150,000 | $0.20 (billed to OpenRouter) |

## Per-Agent Configuration

You can also override the model for specific agents in the database:

```sql
-- Use Claude Sonnet for GOD System synthesis
UPDATE agent_configs
SET task_type_override = 'claude-sonnet'
WHERE agent_key = 'god_synthesis' AND brand_id = 'your-brand-id';

-- Use Haiku for Writer
UPDATE agent_configs
SET task_type_override = 'claude-haiku'
WHERE agent_key = 'writer' AND brand_id = 'your-brand-id';
```

## Testing

Test that your Claude subscription is working:

```python
import asyncio
from content_engine.utils.llm_client import call_llm

async def test_claude():
    result = await call_llm(
        prompt="Hello! Can you introduce yourself?",
        brand_id="test-brand",
        context="test",
        action="test_claude",
        task_type="creative"
    )
    print(f"Model used: {result.model_used}")
    print(f"Response: {result.content}")

asyncio.run(test_claude())
```

Expected output when `USE_CLAUDE_SUBSCRIPTION=true`:
```
Model used: claude-3-5-haiku-20241022
Response: Hello! I'm Claude, an AI assistant...
```

## Monitoring

Track costs in the database:

```sql
-- Check which models are being used
SELECT
    model,
    COUNT(*) as call_count,
    SUM(prompt_tokens) as total_input_tokens,
    SUM(completion_tokens) as total_output_tokens
FROM cost_tracking
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY model
ORDER BY call_count DESC;

-- Check cost by agent
SELECT
    context,
    action,
    model,
    COUNT(*) as call_count
FROM cost_tracking
WHERE brand_id = 'your-brand-id'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY context, action, model
ORDER BY call_count DESC;
```

## Troubleshooting

### "All LLM routing options failed"

**Cause:** Missing or invalid API key

**Solution:**
```bash
# Check your .env
echo $ANTHROPIC_API_KEY

# Verify it's not empty
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "ANTHROPIC_API_KEY is not set!"
fi
```

### High Costs Unexpectedly

**Cause:** Using Sonnet instead of Haiku for simple tasks

**Solution:**
```bash
# Check which task types are using which models
SELECT context, action, model, COUNT(*)
FROM cost_tracking
WHERE created_at > NOW() - INTERVAL '1 day'
GROUP BY context, action, model
ORDER BY COUNT(*) DESC;
```

### Not Using Claude Subscription

**Cause:** `USE_CLAUDE_SUBSCRIPTION` not set to `true`

**Solution:**
```bash
# Check config
python -c "from content_engine.config import settings; print(settings.use_claude_subscription)"

# Should print: True
```

## Recommended Configuration

### Development (Free)
```bash
USE_CLAUDE_SUBSCRIPTION=false
OPENROUTER_API_KEY=your-key
```

### Production (Claude Subscription)
```bash
USE_CLAUDE_SUBSCRIPTION=true
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
```

### Hybrid (Free + Claude for Critical)
```bash
USE_CLAUDE_SUBSCRIPTION=false
OPENROUTER_API_KEY=your-key
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx

# Override specific agents in DB to use Claude
```

## Summary

- ✅ **Yes**, you can use your Claude subscription
- ✅ Set `USE_CLAUDE_SUBSCRIPTION=true` in `.env`
- ✅ Add `ANTHROPIC_API_KEY` from console.anthropic.com
- ✅ System automatically routes to appropriate Claude model
- ✅ Costs charged to your Claude subscription credits

**Cost:** Depends on your usage, but typically:
- Haiku: ~$0.20 per 100 drafts
- Sonnet: ~$2.40 per 100 drafts

For most content generation tasks, **Haiku** (used for creative tasks) provides excellent quality at low cost.
