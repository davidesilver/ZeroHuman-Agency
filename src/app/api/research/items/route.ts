import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import type { Database } from '@/lib/types/database.types'

type ItemStatus = Database['public']['Enums']['item_status']
type RetrieverType = Database['public']['Enums']['retriever_type']

export async function GET(request: Request) {
  const supabase = await createClient()
  const { searchParams } = new URL(request.url)

  const status = searchParams.get('status') as ItemStatus | null
  const runId = searchParams.get('run_id')
  const retriever = searchParams.get('retriever') as RetrieverType | null
  const sortBy = searchParams.get('sort_by') || 'created_at'
  const sortOrder = searchParams.get('sort_order') || 'desc'
  const page = parseInt(searchParams.get('page') || '1')
  const perPage = Math.min(parseInt(searchParams.get('per_page') || '20'), 100)

  let query = supabase
    .from('research_items')
    .select('*, scores(*)', { count: 'exact' })
    .order(sortBy, { ascending: sortOrder === 'asc' })
    .range((page - 1) * perPage, page * perPage - 1)

  if (status) query = query.eq('status', status)
  if (runId) query = query.eq('run_id', runId)
  if (retriever) query = query.eq('retriever_type', retriever)

  const { data, error, count } = await query

  if (error) return errorResponse(error.message, 500)

  return jsonResponse({
    items: data,
    meta: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) },
  })
}
