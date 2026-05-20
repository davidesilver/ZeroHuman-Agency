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
 *
 * PATCH /api/system/config
 *
 * Writes one or more env-var key/value pairs to .env.local (local dev only).
 * Used by the Setup Wizard to save API keys without manual file editing.
 * Only whitelisted keys are accepted.
 */
import { NextRequest } from 'next/server'
import { writeFileSync, renameSync, existsSync, readFileSync } from 'fs'
import { resolve } from 'path'
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
      tavily:      isSet('TAVILY_API_KEY'),
      youtube:     isSet('YOUTUBE_API_KEY'),
      resend:      isSet('RESEND_API_KEY'),
      firecrawl:   isSet('FIRECRAWL_API_KEY'),
    },
    research_tier: isSet('SERPER_API_KEY')
      ? 'premium'
      : isSet('TAVILY_API_KEY')
        ? 'tavily'
        : 'free',
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

// ── PATCH: write env vars to .env.local ───────────────────────────────────────

/** Keys that the Setup Wizard is allowed to write via PATCH. */
const WRITABLE_KEYS = new Set([
  'ANTHROPIC_API_KEY',
  'OPENROUTER_API_KEY',
  'OPENAI_API_KEY',
  'SERPER_API_KEY',
  'TAVILY_API_KEY',
  'YOUTUBE_API_KEY',
  'STABILITY_API_KEY',
  'REPLICATE_API_TOKEN',
  'FIRECRAWL_API_KEY',
  'RESEND_API_KEY',
  'BREVO_API_KEY',
  'SENDGRID_API_KEY',
  'NEWSLETTER_FROM_EMAIL',
  'NEWSLETTER_FROM_NAME',
  'FROM_EMAIL',
  'FROM_NAME',
  'TELEGRAM_BOT_TOKEN',
  'TELEGRAM_CHAT_ID',
  'POSTIZ_API_KEY',
  'POSTIZ_API_URL',
])

function getEnvPath(): string {
  return resolve(process.cwd(), '.env.local')
}

function parseEnvFile(content: string): Record<string, string> {
  const result: Record<string, string> = {}
  for (const line of content.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const idx = trimmed.indexOf('=')
    if (idx === -1) continue
    result[trimmed.slice(0, idx).trim()] = trimmed.slice(idx + 1).trim()
  }
  return result
}

function serializeEnvFile(entries: Record<string, string>): string {
  return Object.entries(entries).map(([k, v]) => `${k}=${v}`).join('\n') + '\n'
}

export async function PATCH(req: NextRequest) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  let body: Record<string, string>
  try {
    body = await req.json()
  } catch {
    return jsonResponse({ error: 'Invalid JSON' }, 400)
  }

  // Reject unknown keys
  const rejected = Object.keys(body).filter(k => !WRITABLE_KEYS.has(k))
  if (rejected.length > 0) {
    return jsonResponse({ error: `Disallowed keys: ${rejected.join(', ')}` }, 400)
  }

  try {
    const envPath = getEnvPath()
    const existing = existsSync(envPath) ? parseEnvFile(readFileSync(envPath, 'utf-8')) : {}
    const updated = { ...existing, ...body }
    const tmpPath = envPath + '.tmp'
    writeFileSync(tmpPath, serializeEnvFile(updated), 'utf-8')
    renameSync(tmpPath, envPath)
    return jsonResponse({ success: true, updated: Object.keys(body) })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    return jsonResponse({ success: false, error: msg }, 500)
  }
}
