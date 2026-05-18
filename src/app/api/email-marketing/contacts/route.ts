import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend, errorResponse } from '@/lib/api-helpers'

/**
 * POST /api/email-marketing/contacts
 *
 * Body (JSON):   { contacts: [{email, first_name?, last_name?, attributes?}] }
 * Body (CSV):    raw CSV text with email header (content-type: text/csv)
 * Query param:   list_id (optional Brevo list ID to add contacts to)
 *
 * Proxies to Python backend: POST /email-marketing/contacts
 * Returns: { synced: number, errors: [{email, reason}] }
 */
export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const contentType = request.headers.get('content-type') ?? ''
  const url = new URL(request.url)
  const listId = url.searchParams.get('list_id')

  try {
    if (contentType.includes('text/csv')) {
      const csvText = await request.text()
      return proxyToBackend('/email-marketing/contacts', {
        method: 'POST',
        body: { csv: csvText, list_id: listId ? parseInt(listId) : null },
      })
    }

    const body = await request.json()
    return proxyToBackend('/email-marketing/contacts', {
      method: 'POST',
      body: { ...body, list_id: listId ? parseInt(listId) : null },
    })
  } catch {
    return errorResponse('Invalid request body', 400)
  }
}
