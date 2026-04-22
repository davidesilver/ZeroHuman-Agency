/**
 * POST /api/memory/discover — fetch a URL and extract candidate memory facts (preview)
 *
 * P3.2: Proxies to Python backend /api/memory/discover.
 * Nothing is persisted — returns candidates for UI review.
 * User calls /api/memory/consolidate to persist selected facts.
 */
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'
import { NextRequest } from 'next/server'

export async function POST(request: NextRequest) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const body = await request.json()

  return proxyToBackend('/api/memory/discover', {
    method: 'POST',
    body: {
      ...body,
      // Ensure brand_id is set to the active brand if not explicitly overridden
      brand_id: body.brand_id ?? auth.activeBrandId,
    },
  })
}
