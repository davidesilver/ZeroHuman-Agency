import { NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const supabase = await createClient()

    const { data: session, error: sessionError } = await supabase
      .from('writing_lab_sessions')
      .select('*')
      .eq('id', id)
      .single()

    if (sessionError) return errorResponse(sessionError.message, 404)

    const { data: rounds, error: roundsError } = await supabase
      .from('writing_lab_rounds')
      .select('*')
      .eq('session_id', id)
      .order('round_number', { ascending: true })

    if (roundsError) return errorResponse(roundsError.message, 500)

    return jsonResponse({ session, rounds: rounds || [] })
  } catch {
    return errorResponse('Failed to fetch session', 500)
  }
}
