import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend, errorResponse } from '@/lib/api-helpers'

/** POST /api/research/competitor — start spider for list of URLs */
export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  try {
    const body = await request.json()
    return proxyToBackend('/research/competitor', { method: 'POST', body })
  } catch {
    return errorResponse('Invalid request body', 400)
  }
}
