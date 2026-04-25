import { proxyToBackend } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  return proxyToBackend('/social/integrations')
}
