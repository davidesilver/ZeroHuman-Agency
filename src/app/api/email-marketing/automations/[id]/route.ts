import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend, errorResponse } from '@/lib/api-helpers'

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id } = await params
  try {
    const body = await request.json()
    return proxyToBackend(`/email-marketing/automations/${id}`, { method: 'PATCH', body })
  } catch {
    return errorResponse('Invalid request body', 400)
  }
}
