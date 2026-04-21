import { NextRequest } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

// C-03: access_token is NEVER sent from the frontend.
// The backend reads OAuth tokens from brands.social_accounts in the DB.
// Only draft_id is forwarded; brand_id comes from the JWT (forwarded by proxyToBackend).
export async function POST(request: NextRequest) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const body = await request.json()

  // Strip any accidental access_token from client-sent body (defensive)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { access_token: _removed, ...safeBody } = body

  return proxyToBackend('/api/social/publish/linkedin', { method: 'POST', body: safeBody })
}
