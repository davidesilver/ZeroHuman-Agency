import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend, errorResponse } from '@/lib/api-helpers'

/** GET /api/research/deep?status=&limit= */
export async function GET(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const url = new URL(request.url)
  const params = url.searchParams.toString()
  return proxyToBackend(`/research/deep${params ? `?${params}` : ''}`, { method: 'GET' })
}

/** POST /api/research/deep — start a deep research job */
export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  try {
    const body = await request.json()
    return proxyToBackend('/research/deep', { method: 'POST', body })
  } catch {
    return errorResponse('Invalid request body', 400)
  }
}
