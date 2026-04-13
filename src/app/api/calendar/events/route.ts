import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: Request) {
  try {
    // C-07: resolve brand_id from authenticated session — no hardcoded UUID
    const { auth, response } = await requireAuth()
    if (!auth) return response

    const { searchParams } = new URL(request.url)
    const year = parseInt(searchParams.get('year') || new Date().getFullYear().toString())
    const month = parseInt(searchParams.get('month') || new Date().getMonth().toString())

    // Clamp month to valid range (0–11)
    const safeMonth = Math.max(0, Math.min(11, month))
    const startDate = new Date(year, safeMonth, 1).toISOString()
    const endDate = new Date(year, safeMonth + 1, 0, 23, 59, 59).toISOString()

    const supabase = await createClient()

    // M-04: explicitly scope by brand_id (defence-in-depth alongside RLS)
    const { data, error } = await supabase
      .from('calendar_events')
      .select('id, title, event_type, scheduled_at, status, content_draft_id')
      .eq('brand_id', auth.brandId)
      .gte('scheduled_at', startDate)
      .lte('scheduled_at', endDate)
      .order('scheduled_at', { ascending: true })

    if (error) return errorResponse('Failed to fetch events', 500)

    // Also get scheduled drafts that might not have calendar events
    const { data: scheduledDrafts } = await supabase
      .from('content_drafts')
      .select('id, title, platform, content_type, scheduled_at, status')
      .eq('brand_id', auth.brandId)
      .eq('status', 'scheduled')
      .gte('scheduled_at', startDate)
      .lte('scheduled_at', endDate)
      .order('scheduled_at', { ascending: true })

    return jsonResponse({
      events: data || [],
      scheduled_drafts: scheduledDrafts || [],
    })
  } catch {
    return errorResponse('Failed to fetch calendar events', 500)
  }
}
