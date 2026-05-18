import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend, errorResponse } from '@/lib/api-helpers'

export async function GET(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  return proxyToBackend('/video/templates', { method: 'GET' })
}

export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  try {
    const body = await request.json()
    return proxyToBackend('/video/templates', { method: 'POST', body })
  } catch {
    return errorResponse('Invalid request body', 400)
  }
}
