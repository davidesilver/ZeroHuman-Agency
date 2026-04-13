import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: Request) {
  // C-07: resolve brand_id from authenticated session
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const supabase = await createClient()
  const { searchParams } = new URL(request.url)
  const page = Math.max(1, parseInt(searchParams.get('page') || '1'))
  const perPage = Math.min(parseInt(searchParams.get('per_page') || '20'), 100)

  // M-05: explicitly scope by brand_id (defence-in-depth alongside RLS)
  const { data, error, count } = await supabase
    .from('newsletters')
    .select('*', { count: 'exact' })
    .eq('brand_id', auth.brandId)
    .order('created_at', { ascending: false })
    .range((page - 1) * perPage, page * perPage - 1)

  if (error) return errorResponse('Failed to fetch newsletters', 500)

  return jsonResponse({
    newsletters: data,
    meta: { page, per_page: perPage, total: count || 0 },
  })
}
