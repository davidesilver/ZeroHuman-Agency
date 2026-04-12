import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'

export async function GET() {
  const supabase = await createClient()

  const { data, error } = await supabase
    .from('research_items')
    .select('status')

  if (error) return errorResponse(error.message, 500)

  const counts: Record<string, number> = { total: 0, new: 0, scored: 0, approved: 0, rejected: 0, archived: 0 }
  for (const item of data || []) {
    counts.total++
    const s = item.status
    if (s && s in counts) counts[s]++
  }

  return jsonResponse(counts)
}
