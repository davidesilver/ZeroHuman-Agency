import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'

export async function GET(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  return proxyToBackend('/video/templates', { method: 'GET' })
}
