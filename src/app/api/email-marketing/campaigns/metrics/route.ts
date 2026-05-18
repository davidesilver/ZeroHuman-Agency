import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'

export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  return proxyToBackend('/email-marketing/campaigns/metrics', { method: 'GET' })
}
