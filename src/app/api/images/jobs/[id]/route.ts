import { proxyToBackend } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id } = await params
  return proxyToBackend(`/images/jobs/${id}`)
}
