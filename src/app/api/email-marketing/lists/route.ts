import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend, errorResponse } from '@/lib/api-helpers'

/**
 * GET /api/email-marketing/lists
 * Returns all Brevo lists for the active brand.
 *
 * POST /api/email-marketing/lists
 * Body: { name: string, folder_id?: number }
 * Creates a new Brevo contact list.
 */
export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  return proxyToBackend('/email-marketing/lists', { method: 'GET' })
}

export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  try {
    const body = await request.json()
    return proxyToBackend('/email-marketing/lists', { method: 'POST', body })
  } catch {
    return errorResponse('Invalid request body', 400)
  }
}
