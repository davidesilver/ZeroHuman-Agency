import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'

export async function GET(request: Request) {
  const supabase = await createClient()
  const { searchParams } = new URL(request.url)
  const page = parseInt(searchParams.get('page') || '1')
  const perPage = Math.min(parseInt(searchParams.get('per_page') || '20'), 100)

  const { data, error, count } = await supabase
    .from('newsletters')
    .select('*', { count: 'exact' })
    .order('created_at', { ascending: false })
    .range((page - 1) * perPage, page * perPage - 1)

  if (error) return errorResponse(error.message, 500)

  return jsonResponse({
    newsletters: data,
    meta: { page, per_page: perPage, total: count || 0 },
  })
}
