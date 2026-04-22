/**
 * POST /api/memory/consolidate — trigger consolidation for the active brand
 *
 * Proxies to the Python backend (scheduler-secret protected there too,
 * but Next.js adds an extra auth layer to prevent anonymous triggering).
 */
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend, errorResponse } from '@/lib/api-helpers'

export async function POST() {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  // Use the JWT-authenticated endpoint (not the scheduler-secret-protected one).
  // The scheduler cron calls /api/memory/consolidate with X-Scheduler-Secret.
  // The dashboard UI calls /api/memory/consolidate-user with the user's JWT.
  return proxyToBackend('/api/memory/consolidate-user', {
    method: 'POST',
    body: { brand_id: auth.activeBrandId },
  })
}
