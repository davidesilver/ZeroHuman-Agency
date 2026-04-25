import { errorResponse, proxyToBackend } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  return proxyToBackend('/social/integrations/mine')
}

export async function POST(req: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const body = await req.json().catch(() => null)
  if (!body) return errorResponse('Invalid JSON', 400)
  return proxyToBackend('/social/integrations/mine', { method: 'POST', body })
}
