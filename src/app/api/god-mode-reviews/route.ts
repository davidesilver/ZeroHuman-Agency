import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function GET(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  try {
    const { searchParams } = new URL(request.url)
    const draftId = searchParams.get('draft_id')

    const supabase = await createClient()

    let query = supabase
      .from('god_mode_reviews')
      .select('*, content_drafts!inner(brand_id)')
      .eq('content_drafts.brand_id', auth.brandId)
      .order('created_at', { ascending: false })
      .limit(1)

    if (draftId) {
      query = query.eq('draft_id', draftId)
    }

    const { data, error } = await query

    if (error) return errorResponse(error.message, 500)

    const review = data?.[0]
    if (!review) return jsonResponse(null)

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { content_drafts: _omit, ...rest } = review as Record<string, unknown>
    return jsonResponse(rest)
  } catch {
    return errorResponse('Failed to fetch GOD mode review', 500)
  }
}
