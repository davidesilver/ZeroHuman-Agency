import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend, errorResponse } from '@/lib/api-helpers'

export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  let body: unknown
  try {
    body = await request.json()
  } catch {
    return errorResponse('Invalid JSON body', 400)
  }

  return proxyToBackend('/api/brand-discovery', { method: 'POST', body })
}
