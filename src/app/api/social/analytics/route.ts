import { proxyToBackend } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function GET(req: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const url = new URL(req.url)
  const integrationId = url.searchParams.get('integration_id')
  const days = url.searchParams.get('days') || '7'
  if (!integrationId) {
    return new Response(
      JSON.stringify({ success: false, error: { message: 'integration_id required' } }),
      { status: 400, headers: { 'Content-Type': 'application/json' } },
    )
  }
  return proxyToBackend(`/social/analytics?integration_id=${integrationId}&days=${days}`)
}
