import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend, errorResponse } from '@/lib/api-helpers'

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id } = await params
  try {
    const body = await request.json().catch(() => ({}))
    return proxyToBackend(`/research/deep/${id}/generate-ideas`, { method: 'POST', body })
  } catch {
    return errorResponse('Invalid request', 400)
  }
}
