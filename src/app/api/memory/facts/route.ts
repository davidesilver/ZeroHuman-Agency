/**
 * GET  /api/memory/facts   — list semantic memory facts for the active brand
 * POST /api/memory/facts   — create a new fact (proxied to Python backend)
 * PATCH + DELETE proxied via /api/memory/facts/[id]
 */
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse, proxyToBackend } from '@/lib/api-helpers'
import { NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { searchParams } = new URL(request.url)
  const kind = searchParams.get('kind')
  const tier = searchParams.get('tier')
  const limit = Math.min(parseInt(searchParams.get('limit') || '100', 10), 500)

  const supabase = await createClient()
  const now = new Date().toISOString()

  let q = supabase
    .from('memory_semantic')
    .select(
      'id,kind,statement,tier,importance,asserted_at,expires_at,retrieval_hits,last_retrieved,source_kind,source_id,supersedes_id,metadata'
    )
    .eq('brand_id', auth.activeBrandId)
    .or(`expires_at.is.null,expires_at.gt.${now}`)
    .order('asserted_at', { ascending: false })
    .limit(limit)

  // Cast to satisfy the strongly-typed enum columns generated from DB types
  if (kind) q = q.eq('kind', kind as 'tone_rule' | 'principle' | 'gold_example' | 'discard_example' | 'brand_fact' | 'audience_insight')
  if (tier) q = q.eq('tier', tier as 'core' | 'persistent' | 'standard' | 'transient')

  const { data, error } = await q
  if (error) return errorResponse('Failed to fetch memory facts', 500)

  return jsonResponse(data || [])
}

export async function POST(request: NextRequest) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const body = await request.json()
  const { kind, statement, tier, importance } = body

  return proxyToBackend('/api/memory/facts', {
    method: 'POST',
    body: { kind, statement, tier, importance, brand_id: auth.activeBrandId },
  })
}
