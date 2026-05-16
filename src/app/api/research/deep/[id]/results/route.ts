import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'

export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id } = await params
  return proxyToBackend(`/research/deep/${id}/results`, { method: 'GET' })
}
