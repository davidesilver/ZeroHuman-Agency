import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'

export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const body = await request.json()
  return proxyToBackend('/llm/gateways/probe', { method: 'POST', body })
}
