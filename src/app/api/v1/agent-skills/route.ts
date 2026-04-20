import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { createClient } from '@/lib/supabase/server'

const VALID_PRIORITIES = new Set(['high', 'medium', 'low'])

export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('agent_skills')
    .select('*')
    .eq('brand_id', auth.brandId)
    .order('created_at', { ascending: false })

  if (error) return errorResponse('Failed to fetch agent skills', 500)

  return jsonResponse(data)
}

export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  let body: {
    target_agent?: string
    skill_name?: string
    description?: string
    instructions?: string
    priority?: string
    tags?: string[]
  }
  try {
    body = await request.json()
  } catch {
    return errorResponse('Invalid JSON body', 400)
  }

  const { target_agent, skill_name, description, instructions, priority, tags } = body
  if (!target_agent || !skill_name) {
    return errorResponse('target_agent and skill_name are required', 400)
  }
  if (priority && !VALID_PRIORITIES.has(priority)) {
    return errorResponse('priority must be high, medium, or low', 400)
  }

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('agent_skills')
    .insert({
      brand_id: auth.brandId,
      target_agent,
      skill_name,
      description: description ?? '',
      instructions: instructions ?? '',
      priority: priority ?? 'medium',
      tags: tags ?? [],
    })
    .select()
    .single()

  if (error) return errorResponse('Failed to create agent skill', 500)

  return jsonResponse(data, 201)
}
