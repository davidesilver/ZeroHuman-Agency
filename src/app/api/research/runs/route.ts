import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import type { Database } from '@/lib/types/database.types'

type RunStatus = Database['public']['Enums']['run_status']

export async function GET(request: Request) {
  const supabase = await createClient()
  const { searchParams } = new URL(request.url)
  const status = searchParams.get('status') as RunStatus | null
  const page = parseInt(searchParams.get('page') || '1')
  const perPage = parseInt(searchParams.get('per_page') || '20')

  let query = supabase
    .from('research_runs')
    .select('*', { count: 'exact' })
    .order('created_at', { ascending: false })
    .range((page - 1) * perPage, page * perPage - 1)

  if (status) query = query.eq('status', status)

  const { data, error } = await query

  if (error) return errorResponse(error.message, 500)

  return jsonResponse(data, 200)
}
