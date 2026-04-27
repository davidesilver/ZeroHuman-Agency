/**
 * GET /api/system/config
 *
 * Returns the current runtime configuration derived from environment variables.
 * This lets client components (like the Settings page) display live config
 * values without embedding process.env in client bundles.
 *
 * Security: only returns whether sensitive keys are SET (boolean), never
 * their actual values. Non-sensitive config values (model names, thresholds,
 * URLs that the user already pastes themselves) are returned as strings.
 */
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { jsonResponse } from '@/lib/api-helpers'

function isSet(key: string): boolean {
  const v = process.env[key]
  return typeof v === 'string' && v.trim().length > 0
}

function envStr(key: string, fallback: string): string {
  return process.env[key]?.trim() || fallback
}

function envNum(key: string, fallback: number): number {
  const v = parseFloat(process.env[key] || '')
  return isNaN(v) ? fallback : v
}

function envNumNullable(key: string): number | null {
  const v = process.env[key]
  if (!v || v.trim() === '') return null
  const n = parseFloat(v)
  return isNaN(n) ? null : n
}

export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  return jsonResponse({
    api_keys: {
      anthropic:   isSet('ANTHROPIC_API_KEY'),
      openrouter:  isSet('OPENROUTER_API_KEY'),
      serper:      isSet('SERPER_API_KEY'),
      youtube:     isSet('YOUTUBE_API_KEY'),
      resend:      isSet('RESEND_API_KEY'),
      firecrawl:   isSet('FIRECRAWL_API_KEY'),
    },
    image_backends: {
      default_backend: envStr('DEFAULT_IMAGE_BACKEND', 'mock'),
      default_model:   envStr('DEFAULT_IMAGE_MODEL',   'mock-v1'),
      replicate:       isSet('REPLICATE_API_TOKEN'),
      openai:          isSet('OPENAI_API_KEY'),
      pillo:           isSet('PILLO_API_KEY'),
      // Re-uses the same env var as the LLM provider; surfaced here so users
      // can verify image generation via OpenRouter/Anthropic also has a key.
      openrouter:      isSet('OPENROUTER_API_KEY'),
      anthropic:       isSet('ANTHROPIC_API_KEY'),
    },
    postiz: {
      mode:     envStr('POSTIZ_MODE',    'disabled'),  // disabled | self_hosted | cloud
      api_url:  envStr('POSTIZ_API_URL', ''),
      api_key:  isSet('POSTIZ_API_KEY'),
    },
    alerts: {
      telegram_bot:  isSet('TELEGRAM_BOT_TOKEN'),
      telegram_chat: isSet('TELEGRAM_CHAT_ID'),
    },
    operations: {
      scheduler_secret:   isSet('SCHEDULER_SECRET'),
      python_backend_url: envStr('PYTHON_BACKEND_URL', ''),
      allowed_origins:    envStr('ALLOWED_ORIGINS',    ''),
      scheduler_brand_id: envStr('SCHEDULER_BRAND_ID', ''),  // empty → fan-out
    },
    llm: {
      scoring_model:       envStr('SCORING_MODEL',           'claude-sonnet-4-20250514'),
      auto_approve_score:  envNum('AUTO_APPROVE_SCORE',      8.0),
      auto_reject_score:   envNum('AUTO_REJECT_SCORE',       3.0),
    },
    email: {
      from_email: envStr('NEWSLETTER_FROM_EMAIL', envStr('FROM_EMAIL', '')),
      from_name:  envStr('NEWSLETTER_FROM_NAME',  envStr('FROM_NAME',  'Content Engine')),
    },
    research: {
      dedup_threshold:     envNum('DEDUP_THRESHOLD',         0.85),
      max_items_retriever: envNum('MAX_ITEMS_PER_RETRIEVER', 100),
    },
    scheduler: {
      daily_pipeline:    envStr('CRON_DAILY_PIPELINE',    '07:00 CET'),
      feedback_loop:     envStr('CRON_FEEDBACK_LOOP',     '02:00 CET'),
      publish_scheduled: envStr('CRON_PUBLISH_SCHEDULED', 'every 10min'),
    },
    budget: {
      daily_cap_usd: envNumNullable('DAILY_COST_CAP_USD'),
    },
    social: {
      linkedin:  isSet('LINKEDIN_TOKEN'),
      twitter:   isSet('TWITTER_BEARER_TOKEN'),
      instagram: isSet('INSTAGRAM_TOKEN'),
      tiktok:    isSet('TIKTOK_TOKEN'),
    },
  })
}
