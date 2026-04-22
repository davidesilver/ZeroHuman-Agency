/**
 * GET /api/memory/episodic — last N events from vw_memory_episodic
 */
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { searchParams } = new URL(request.url)
  const limit = Math.min(parseInt(searchParams.get('limit') || '100', 10), 500)

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('vw_memory_episodic')
    .select('event_kind,subject_kind,subject_id,summary,payload,occurred_at')
    .eq('brand_id', auth.activeBrandId)
    .order('occurred_at', { ascending: false })
    .limit(limit)

  if (error) return errorResponse('Failed to fetch episodic events', 500)

  return jsonResponse(data || [])
}
