import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import type { Database } from '@/lib/types/database.types'

type NewsletterUpdate = Database['public']['Tables']['newsletters']['Update']

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const supabase = await createClient()
  const { data, error } = await supabase
    .from('newsletters')
    .select('*')
    .eq('id', id)
    .single()

  if (error) return errorResponse(error.message, 500)
  if (!data) return errorResponse('Newsletter not found', 404)
  return jsonResponse(data)
}

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const body = await request.json()
  const updates: NewsletterUpdate = {}
  if ('status' in body) updates.status = body.status
  if ('title' in body) updates.title = body.title
  if ('slot_sistema_id' in body) updates.slot_sistema_id = body.slot_sistema_id
  if ('slot_strumento_id' in body) updates.slot_strumento_id = body.slot_strumento_id
  if ('slot_mossa_id' in body) updates.slot_mossa_id = body.slot_mossa_id
  if ('scheduled_at' in body) updates.scheduled_at = body.scheduled_at

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('newsletters')
    .update(updates)
    .eq('id', id)
    .select()
    .single()

  if (error) return errorResponse(error.message, 500)
  if (!data) return errorResponse('Newsletter not found', 404)
  return jsonResponse(data)
}
