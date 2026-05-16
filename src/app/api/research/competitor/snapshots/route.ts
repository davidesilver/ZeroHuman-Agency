import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'

/** GET /api/research/competitor/snapshots?url=&limit= */
export async function GET(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const url = new URL(request.url)
  const params = url.searchParams.toString()
  return proxyToBackend(`/research/competitor/snapshots${params ? `?${params}` : ''}`, { method: 'GET' })
}
