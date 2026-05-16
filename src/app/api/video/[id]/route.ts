import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'

/** GET /api/video/:id — poll render status */
export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id } = await params
  return proxyToBackend(`/video/${id}/status`, { method: 'GET' })
}
