import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function GET() {
  // Require auth — unauthenticated callers must not enumerate brands
  const { auth, response } = await requireAuth()
  if (!auth) return response

  try {
    const supabase = await createClient()

    // RLS on brands table scopes this to auth_user_brand_id() automatically
    const { data, error } = await supabase
      .from('brands')
      .select('id, name, slug')
      .order('name')

    if (error) return errorResponse('Failed to fetch brands', 500)

    return jsonResponse(data || [])
  } catch {
    return errorResponse('Failed to fetch brands', 500)
  }
}
