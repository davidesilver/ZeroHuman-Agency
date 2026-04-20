import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { createClient } from '@/lib/supabase/server'

export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('agent_configs')
    .select('*')
    .eq('brand_id', auth.brandId)
    .order('created_at', { ascending: false })

  if (error) return errorResponse('Failed to fetch agent configs', 500)

  return jsonResponse(data)
}

export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  let body: { agent_key?: string; agent_name?: string; identity?: string }
  try {
    body = await request.json()
  } catch {
    return errorResponse('Invalid JSON body', 400)
  }

  const { agent_key, agent_name, identity } = body
  if (!agent_key || !agent_name) {
    return errorResponse('agent_key and agent_name are required', 400)
  }

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('agent_configs')
    .insert({
      brand_id: auth.brandId,
      agent_key,
      agent_name,
      identity: identity ?? '',
    })
    .select()
    .single()

  if (error) {
    if (error.code === '23505') {
      return errorResponse('An agent with this key already exists for this brand', 409)
    }
    return errorResponse('Failed to create agent config', 500)
  }

  return jsonResponse(data, 201)
}
