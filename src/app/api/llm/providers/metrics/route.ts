import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'

/** GET /api/llm/providers/metrics?window=7d */
export async function GET(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const url = new URL(request.url)
  const window = url.searchParams.get('window') ?? '7d'
  return proxyToBackend(`/llm/providers/metrics?window=${window}`, { method: 'GET' })
}
