import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import type { Database } from '@/lib/types/database.types'

type DraftStatus = Database['public']['Enums']['draft_status']

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const supabase = await createClient()
  const { data, error } = await supabase
    .from('content_drafts')
    .select('*, god_mode_reviews(*)')
    .eq('id', id)
    .single()

  if (error) return errorResponse(error.message, 500)
  if (!data) return errorResponse('Draft not found', 404)
  return jsonResponse(data)
}

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const body = await request.json()
  const allowed = ['status', 'title', 'body', 'scheduled_at'] as const
  const updates: Record<string, unknown> = {}
  for (const key of allowed) {
    if (key in body) updates[key] = body[key]
  }
  if (Object.keys(updates).length === 0) return errorResponse('No valid fields', 400)

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('content_drafts')
    .update(updates as { status?: DraftStatus })
    .eq('id', id)
    .select()
    .single()

  if (error) return errorResponse(error.message, 500)
  if (!data) return errorResponse('Draft not found', 404)
  return jsonResponse(data)
}
