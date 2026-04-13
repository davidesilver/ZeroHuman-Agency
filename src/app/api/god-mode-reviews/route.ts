import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const draftId = searchParams.get('draft_id')

    const supabase = await createClient()

    let query = supabase
      .from('god_mode_reviews')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(1)

    if (draftId) {
      query = query.eq('draft_id', draftId)
    }

    const { data, error } = await query

    if (error) return errorResponse(error.message, 500)

    return jsonResponse(data?.[0] || null)
  } catch (err) {
    return errorResponse('Failed to fetch GOD mode review', 500)
  }
}
