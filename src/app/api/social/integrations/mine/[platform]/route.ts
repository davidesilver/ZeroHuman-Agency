import { proxyToBackend } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ platform: string }> },
) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { platform } = await params
  return proxyToBackend(`/social/integrations/mine/${platform}`, { method: 'DELETE' })
}
