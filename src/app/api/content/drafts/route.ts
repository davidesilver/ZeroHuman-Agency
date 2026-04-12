import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import type { Database } from '@/lib/types/database.types'

type DraftStatus = Database['public']['Enums']['draft_status']

export async function GET(request: Request) {
  const supabase = await createClient()
  const { searchParams } = new URL(request.url)

  const status = searchParams.get('status') as DraftStatus | null
  const contentType = searchParams.get('content_type')
  const platform = searchParams.get('platform')
  const page = parseInt(searchParams.get('page') || '1')
  const perPage = Math.min(parseInt(searchParams.get('per_page') || '20'), 100)

  let query = supabase
    .from('content_drafts')
    .select('*', { count: 'exact' })
    .order('created_at', { ascending: false })
    .range((page - 1) * perPage, page * perPage - 1)

  if (status) query = query.eq('status', status)
  if (contentType) query = query.eq('content_type', contentType as Database['public']['Enums']['content_type'])
  if (platform) query = query.eq('platform', platform as Database['public']['Enums']['platform'])

  const { data, error, count } = await query
  if (error) return errorResponse(error.message, 500)

  return jsonResponse({
    drafts: data,
    meta: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) },
  })
}
