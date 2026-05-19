import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'

export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  return proxyToBackend('/setup/progress', { method: 'GET' })
}

export async function PATCH(req: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const body = await req.json()
  return proxyToBackend('/setup/progress', { method: 'PATCH', body })
}
