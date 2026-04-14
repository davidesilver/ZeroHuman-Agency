import { NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { proxyToBackend } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

type LabStatus = 'active' | 'completed' | 'paused'

export async function GET(request: NextRequest) {
  try {
    const { auth, response } = await requireAuth()
    if (!auth) return response

    const supabase = await createClient()
    const params = request.nextUrl.searchParams
    const status = params.get('status') as LabStatus | null

    let query = supabase
      .from('writing_lab_sessions')
      .select('*')
      .eq('brand_id', auth.brandId)
      .order('created_at', { ascending: false })

    if (status) query = query.eq('status', status)

    const { data, error } = await query

    if (error) return errorResponse(error.message, 500)

    return jsonResponse({ sessions: data || [] })
  } catch (err) {
    return errorResponse('Failed to fetch sessions', 500)
  }
}

export async function POST(request: NextRequest) {
  return proxyToBackend('/api/writing-lab/sessions', {
    method: 'POST',
    body: await request.json(),
  })
}
