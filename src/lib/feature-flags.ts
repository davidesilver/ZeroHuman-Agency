import { createClient } from '@/lib/supabase/server'

/**
 * Read a per-brand feature flag from the database.
 * Uses the authenticated session — RLS applies.
 */
export async function getFeatureFlag(
  brandId: string,
  key: string,
  defaultValue = false,
): Promise<boolean> {
  const supabase = await createClient()
  // Cast table name — database.types.ts is regenerated after migrations are applied
  const { data } = await (supabase as any)
    .from('feature_flags')
    .select('value')
    .eq('brand_id', brandId)
    .eq('key', key)
    .maybeSingle()
  return (data as any)?.value ?? defaultValue
}

/**
 * Write a per-brand feature flag (owner/admin only).
 */
export async function setFeatureFlag(
  brandId: string,
  key: string,
  value: boolean,
): Promise<void> {
  const supabase = await createClient()
  await (supabase as any).from('feature_flags').upsert(
    { brand_id: brandId, key, value },
    { onConflict: 'brand_id,key' },
  )
}

// ── Known flag keys ──────────────────────────────────────────────────────
export const FLAGS = {
  VIDEO_ENABLED: 'video_enabled',
  EMAIL_MARKETING_ENABLED: 'email_marketing_enabled',
  DEEP_RESEARCH_ENABLED: 'deep_research_enabled',
  COMPETITOR_MONITORING_ENABLED: 'competitor_monitoring_enabled',
  LLM_PROVIDER_OPENCLAW_SHARE: 'llm_provider_openclaw_share',
} as const
