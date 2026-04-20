import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { createClient } from '@/lib/supabase/server'
import type { Database } from '@/lib/types/database.types'

type RouteContext = { params: Promise<{ id: string }> }
type AgentConfigUpdate = Database['public']['Tables']['agent_configs']['Update']

export async function PUT(request: Request, { params }: RouteContext) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { id } = await params

  let body: { identity?: string; is_active?: boolean; agent_name?: string }
  try {
    body = await request.json()
  } catch {
    return errorResponse('Invalid JSON body', 400)
  }

  const update: AgentConfigUpdate = { updated_at: new Date().toISOString() }
  if (typeof body.identity === 'string') update.identity = body.identity
  if (typeof body.is_active === 'boolean') update.is_active = body.is_active
  if (typeof body.agent_name === 'string') update.agent_name = body.agent_name

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('agent_configs')
    .update(update)
    .eq('id', id)
    .eq('brand_id', auth.brandId)
    .select()
    .single()

  if (error || !data) return errorResponse('Agent config not found', 404)

  return jsonResponse(data)
}

export async function DELETE(_request: Request, { params }: RouteContext) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { id } = await params

  const supabase = await createClient()
  const { error, count } = await supabase
    .from('agent_configs')
    .delete({ count: 'exact' })
    .eq('id', id)
    .eq('brand_id', auth.brandId)

  if (error) return errorResponse('Failed to delete agent config', 500)
  if (!count) return errorResponse('Agent config not found', 404)

  return jsonResponse({ id })
}
