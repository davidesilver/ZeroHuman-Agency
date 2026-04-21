import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { createClient } from '@/lib/supabase/server'
import type { Database } from '@/lib/types/database.types'

type EventType = Database['public']['Enums']['event_type']

const VALID_EVENT_TYPES = new Set<EventType>(['newsletter', 'social', 'blog_video', 'sponsorship'])

export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  let body: { title?: string; event_type?: string; scheduled_date?: string; scheduled_time?: string }
  try {
    body = await request.json()
  } catch {
    return errorResponse('Invalid JSON body', 400)
  }

  if (!body.title?.trim()) return errorResponse('title is required', 400)
  if (!body.scheduled_date) return errorResponse('scheduled_date is required', 400)
  if (!body.event_type || !VALID_EVENT_TYPES.has(body.event_type as EventType)) {
    return errorResponse('event_type must be newsletter, social, blog_video, or sponsorship', 400)
  }

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('calendar_events')
    .insert({
      brand_id: auth.brandId,
      title: body.title.trim(),
      event_type: body.event_type as EventType,
      scheduled_date: body.scheduled_date,
      scheduled_time: body.scheduled_time || null,
      status: 'planned',
    })
    .select()
    .single()

  if (error) return errorResponse(error.message, 500)

  return jsonResponse(data, 201)
}

export async function GET(request: Request) {
  try {
    // C-07: resolve brand_id from authenticated session — no hardcoded UUID
    const { auth, response } = await requireAuth()
    if (!auth) return response

    const { searchParams } = new URL(request.url)
    const year = parseInt(searchParams.get('year') || new Date().getFullYear().toString())
    const month = parseInt(searchParams.get('month') || new Date().getMonth().toString())

    // Clamp month to valid range (0–11). JS Date months are 0-indexed; SQL `date`
    // columns expect YYYY-MM-DD strings.
    const safeMonth = Math.max(0, Math.min(11, month))
    const pad = (n: number) => String(n).padStart(2, '0')
    const startDate = `${year}-${pad(safeMonth + 1)}-01`
    // Last day of month: day 0 of next month
    const lastDay = new Date(year, safeMonth + 1, 0).getDate()
    const endDate = `${year}-${pad(safeMonth + 1)}-${pad(lastDay)}`

    const supabase = await createClient()

    // Schema truth (migration 001:510-522):
    //   calendar_events(scheduled_date DATE, scheduled_time TIME, draft_id UUID, ...)
    // There is no `scheduled_at` nor `content_draft_id` column.
    // M-04: explicitly scope by brand_id (defence-in-depth alongside RLS)
    const { data, error } = await supabase
      .from('calendar_events')
      .select('id, title, event_type, scheduled_date, scheduled_time, status, draft_id')
      .eq('brand_id', auth.brandId)
      .gte('scheduled_date', startDate)
      .lte('scheduled_date', endDate)
      .order('scheduled_date', { ascending: true })

    if (error) return errorResponse('Failed to fetch events', 500)

    // Also get scheduled drafts that might not have calendar events.
    // content_drafts.scheduled_at IS a timestamptz column (unlike calendar_events),
    // so ISO strings are correct here.
    const startTs = new Date(year, safeMonth, 1).toISOString()
    const endTs = new Date(year, safeMonth + 1, 0, 23, 59, 59).toISOString()
    const { data: scheduledDrafts } = await supabase
      .from('content_drafts')
      .select('id, title, platform, content_type, scheduled_at, status')
      .eq('brand_id', auth.brandId)
      .eq('status', 'scheduled')
      .gte('scheduled_at', startTs)
      .lte('scheduled_at', endTs)
      .order('scheduled_at', { ascending: true })

    return jsonResponse({
      events: data || [],
      scheduled_drafts: scheduledDrafts || [],
    })
  } catch {
    return errorResponse('Failed to fetch calendar events', 500)
  }
}
