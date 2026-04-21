import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  try {
    const supabase = await createClient()
    const { data, error } = await supabase
      .from('brands')
      .select('id, name, slug, topics, tone_of_voice, scoring_weights')
      .order('name')

    if (error) return errorResponse('Failed to fetch brands', 500)

    return jsonResponse(data || [])
  } catch {
    return errorResponse('Failed to fetch brands', 500)
  }
}

export async function POST(request: Request) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) return errorResponse('Unauthorized', 401)

  let body: { name?: string; slug?: string; topics?: string[] }
  try {
    body = await request.json()
  } catch {
    return errorResponse('Invalid JSON body', 400)
  }

  if (!body.name?.trim()) return errorResponse('name is required', 400)
  if (!body.slug?.trim()) return errorResponse('slug is required', 400)

  const slug = body.slug.trim().toLowerCase().replace(/[^a-z0-9-]/g, '-')

  // Use SECURITY DEFINER RPC to bypass RLS bootstrap chicken-and-egg:
  // direct INSERT on brands is denied (no INSERT policy), so we call the
  // function that atomically creates brand + owner user record.
  const { data, error } = await supabase.rpc('create_brand_with_owner', {
    p_name:   body.name.trim(),
    p_slug:   slug,
    p_topics: body.topics || [],
  })

  if (error) {
    if (error.message === 'slug_taken') return errorResponse('A brand with that slug already exists', 409)
    if (error.message === 'user_already_has_brand') return errorResponse('You already have a brand configured', 409)
    return errorResponse(error.message, 500)
  }

  return jsonResponse(data, 201)
}
