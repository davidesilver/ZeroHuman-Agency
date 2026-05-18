import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend, errorResponse, jsonResponse } from '@/lib/api-helpers'

/**
 * POST /api/internal/brand-secrets
 * Body: { provider: string, key_name: string, value: string }
 * Saves an encrypted secret to brand_integrations via Python backend.
 *
 * GET /api/internal/brand-secrets?provider=&key_name=
 * Returns { exists: boolean, updated_at: string | null }
 * Never returns the secret value.
 */
export async function GET(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const url = new URL(request.url)
  const provider = url.searchParams.get('provider')
  const keyName = url.searchParams.get('key_name')

  if (!provider || !keyName) {
    return errorResponse('provider and key_name are required', 400)
  }

  return proxyToBackend(`/internal/brand-secrets?provider=${encodeURIComponent(provider)}&key_name=${encodeURIComponent(keyName)}`, {
    method: 'GET',
  })
}

export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  try {
    const body = await request.json() as { provider?: string; key_name?: string; value?: string }
    if (!body.provider || !body.key_name || !body.value) {
      return errorResponse('provider, key_name, and value are required', 400)
    }
    return proxyToBackend('/internal/brand-secrets', { method: 'POST', body })
  } catch {
    return errorResponse('Invalid request body', 400)
  }
}

export async function DELETE(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const url = new URL(request.url)
  const provider = url.searchParams.get('provider')
  const keyName = url.searchParams.get('key_name')

  if (!provider || !keyName) {
    return errorResponse('provider and key_name are required', 400)
  }

  return proxyToBackend(`/internal/brand-secrets?provider=${encodeURIComponent(provider)}&key_name=${encodeURIComponent(keyName)}`, {
    method: 'DELETE',
  })
}
