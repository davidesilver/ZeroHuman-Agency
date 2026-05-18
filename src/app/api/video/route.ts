import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'

/** GET /api/video — list videos for active brand */
export async function GET(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const url = new URL(request.url)
  const params = url.searchParams.toString()
  return proxyToBackend(`/video${params ? `?${params}` : ''}`, { method: 'GET' })
}
