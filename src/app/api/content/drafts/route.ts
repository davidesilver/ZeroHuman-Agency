import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { createClient } from '@/lib/supabase/server'
import type { Database } from '@/lib/types/database.types'

type DraftStatus = Database['public']['Enums']['draft_status']
type ContentType = Database['public']['Enums']['content_type']
type Platform = Database['public']['Enums']['platform']

/**
 * POST /api/content/drafts
 * Creates a new content draft directly in Supabase (no Python backend needed).
 * Used by the Blog Manager "New Post" dialog.
 */
export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  let body: {
    title?: string
    content_type?: string
    platform?: string
    status?: string
    body?: string
  }
  try {
    body = await request.json()
  } catch {
    return errorResponse('Invalid JSON body', 400)
  }

  if (!body.title?.trim()) return errorResponse('title is required', 400)

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('content_drafts')
    .insert({
      brand_id: auth.brandId,
      title: body.title.trim(),
      content_type: (body.content_type || 'blog') as ContentType,
      platform: (body.platform || 'blog') as Platform,
      status: (body.status || 'draft') as DraftStatus,
      body: body.body || null,
    })
    .select()
    .single()

  if (error) return errorResponse(error.message, 500)
  return jsonResponse(data, 201)
}

export async function GET(request: Request) {
  // C-07: resolve brand_id from authenticated session
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const supabase = await createClient()
  const { searchParams } = new URL(request.url)

  const status = searchParams.get('status') as DraftStatus | null
  const contentType = searchParams.get('content_type')
  const platform = searchParams.get('platform')
  const page = Math.max(1, parseInt(searchParams.get('page') || '1'))
  const perPage = Math.min(parseInt(searchParams.get('per_page') || '20'), 100)

  // M-06: explicitly scope by brand_id (defence-in-depth alongside RLS)
  let query = supabase
    .from('content_drafts')
    .select('*', { count: 'exact' })
    .eq('brand_id', auth.brandId)
    .order('created_at', { ascending: false })
    .range((page - 1) * perPage, page * perPage - 1)

  if (status) query = query.eq('status', status)
  if (contentType) query = query.eq('content_type', contentType as Database['public']['Enums']['content_type'])
  if (platform) query = query.eq('platform', platform as Database['public']['Enums']['platform'])

  const { data, error, count } = await query
  if (error) return errorResponse('Failed to fetch drafts', 500)

  return jsonResponse({
    drafts: data,
    meta: {
      page,
      per_page: perPage,
      total: count || 0,
      total_pages: Math.ceil((count || 0) / perPage),
    },
  })
}
