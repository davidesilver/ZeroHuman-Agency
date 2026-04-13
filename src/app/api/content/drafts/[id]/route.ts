import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import type { Database } from '@/lib/types/database.types'

type DraftStatus = Database['public']['Enums']['draft_status']

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  // C-07 / M-06: scope by brand_id to prevent BOLA — accessing another brand's draft by raw ID
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { id } = await params
  const supabase = await createClient()
  const { data, error } = await supabase
    .from('content_drafts')
    .select('*, god_mode_reviews(*)')
    .eq('id', id)
    .eq('brand_id', auth.brandId)   // BOLA guard
    .single()

  if (error) return errorResponse('Failed to fetch draft', 500)
  if (!data) return errorResponse('Draft not found', 404)
  return jsonResponse(data)
}

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  // C-07 / M-07: scope update by brand_id to prevent privilege escalation
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { id } = await params
  const body = await request.json()

  // M-07: whitelist updatable fields — 'status' cannot be set to arbitrary values
  const ALLOWED_STATUSES: DraftStatus[] = ['draft', 'in_review', 'approved', 'archived', 'scheduled']
  const allowed = ['status', 'title', 'body', 'scheduled_at'] as const
  const updates: Record<string, unknown> = {}
  for (const key of allowed) {
    if (key in body) updates[key] = body[key]
  }
  // M-07: validate status against enum
  if ('status' in updates && !ALLOWED_STATUSES.includes(updates.status as DraftStatus)) {
    return errorResponse(`Invalid status. Allowed: ${ALLOWED_STATUSES.join(', ')}`, 400)
  }
  if (Object.keys(updates).length === 0) return errorResponse('No valid fields to update', 400)

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('content_drafts')
    .update(updates as { status?: DraftStatus })
    .eq('id', id)
    .eq('brand_id', auth.brandId)   // BOLA guard
    .select()
    .single()

  if (error) return errorResponse('Failed to update draft', 500)
  if (!data) return errorResponse('Draft not found', 404)
  return jsonResponse(data)
}
