import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

// P10: scope by the user's active brand (was previously summing across every
// brand the user could see via RLS) and use the migration-030 RPC to do the
// GROUP BY in Postgres rather than materialising every row in Node.
export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const supabase = await createClient()

  const { data, error } = await supabase.rpc('research_items_status_counts', {
    p_brand_id: auth.brandId,
  })

  if (error) return errorResponse(error.message, 500)

  const counts = (data ?? {}) as unknown as Record<string, number>
  return jsonResponse({
    total: counts.total ?? 0,
    new: counts.pending ?? 0,
    scored: counts.approved ?? 0,
    approved: counts.approved ?? 0,
    rejected: counts.rejected ?? 0,
    archived: counts.archived ?? 0,
    top_pick: counts.top_pick ?? 0,
  })
}
