import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'

/** GET /api/llm/providers — list registered LLM providers */
export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  return proxyToBackend('/llm/providers', { method: 'GET' })
}
