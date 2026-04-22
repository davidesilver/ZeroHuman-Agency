/**
 * GET /api/system/config
 *
 * Returns the current runtime configuration derived from environment variables.
 * This lets client components (like the Settings page) display live config
 * values without embedding process.env in client bundles.
 *
 * Security: only returns whether sensitive keys are SET (boolean), never
 * their actual values. Non-sensitive config values (model names, thresholds)
 * are returned as strings.
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
    },
    llm: {
      scoring_model:       envStr('SCORING_MODEL',           'claude-sonnet-4-20250514'),
      auto_approve_score:  envNum('AUTO_APPROVE_SCORE',      8.0),
      auto_reject_score:   envNum('AUTO_REJECT_SCORE',       3.0),
    },
    email: {
      from_email: envStr('FROM_EMAIL', ''),
      from_name:  envStr('FROM_NAME',  'Content Engine'),
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
      daily_cap_usd: envNum('DAILY_COST_CAP_USD', 5),
    },
    social: {
      linkedin:  isSet('LINKEDIN_TOKEN'),
      twitter:   isSet('TWITTER_BEARER_TOKEN'),
      instagram: isSet('INSTAGRAM_TOKEN'),
      tiktok:    isSet('TIKTOK_TOKEN'),
    },
  })
}
