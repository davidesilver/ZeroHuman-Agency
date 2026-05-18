import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'

interface Params { provider: string }

export async function POST(request: Request, { params }: { params: Promise<Params> }) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { provider } = await params
  const body = await request.json()
  return proxyToBackend(`/llm/providers/${provider}/key`, { method: 'POST', body })
}

export async function DELETE(_request: Request, { params }: { params: Promise<Params> }) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { provider } = await params
  return proxyToBackend(`/llm/providers/${provider}/key`, { method: 'DELETE' })
}
