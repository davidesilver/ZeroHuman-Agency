import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { createClient } from '@/lib/supabase/server'
import type { Database } from '@/lib/types/database.types'

type RouteContext = { params: Promise<{ id: string }> }
type AgentSkillUpdate = Database['public']['Tables']['agent_skills']['Update']

const VALID_PRIORITIES = new Set(['high', 'medium', 'low'])

export async function PUT(request: Request, { params }: RouteContext) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { id } = await params

  let body: {
    description?: string
    instructions?: string
    is_active?: boolean
    priority?: string
    tags?: string[]
    skill_name?: string
    target_agent?: string
  }
  try {
    body = await request.json()
  } catch {
    return errorResponse('Invalid JSON body', 400)
  }

  if (body.priority && !VALID_PRIORITIES.has(body.priority)) {
    return errorResponse('priority must be high, medium, or low', 400)
  }

  const update: AgentSkillUpdate = { updated_at: new Date().toISOString() }
  if (typeof body.description === 'string') update.description = body.description
  if (typeof body.instructions === 'string') update.instructions = body.instructions
  if (typeof body.is_active === 'boolean') update.is_active = body.is_active
  if (typeof body.priority === 'string') update.priority = body.priority
  if (Array.isArray(body.tags)) update.tags = body.tags
  if (typeof body.skill_name === 'string') update.skill_name = body.skill_name
  if (typeof body.target_agent === 'string') update.target_agent = body.target_agent

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('agent_skills')
    .update(update)
    .eq('id', id)
    .eq('brand_id', auth.brandId)
    .select()
    .single()

  if (error || !data) return errorResponse('Agent skill not found', 404)

  return jsonResponse(data)
}

export async function DELETE(_request: Request, { params }: RouteContext) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { id } = await params

  const supabase = await createClient()
  const { error, count } = await supabase
    .from('agent_skills')
    .delete({ count: 'exact' })
    .eq('id', id)
    .eq('brand_id', auth.brandId)

  if (error) return errorResponse('Failed to delete agent skill', 500)
  if (!count) return errorResponse('Agent skill not found', 404)

  return jsonResponse({ id })
}
