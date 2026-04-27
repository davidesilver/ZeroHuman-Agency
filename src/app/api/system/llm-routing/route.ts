/**
 * GET /api/system/llm-routing
 *
 * Proxies the Python backend's /api/system/llm-routing endpoint, which returns
 * the static capability → model routing matrix from `config/llm_models.py`.
 *
 * The Settings page renders this so operators can see, at a glance, which
 * model is primary and which will be tried as fallback for each task type
 * (creative, scoring, research, …) — without grepping Python source.
 *
 * If the Python backend is unreachable we return a graceful 503 with an
 * empty matrix; the UI then shows a "backend offline" hint instead of
 * crashing.
 */
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { jsonResponse } from '@/lib/api-helpers'
import { createClient } from '@/lib/supabase/server'

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000'

export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const supabase = await createClient()
  const { data: { session } } = await supabase.auth.getSession()

  const headers: Record<string, string> = {}
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }

  try {
    const resp = await fetch(`${PYTHON_BACKEND_URL}/api/system/llm-routing`, {
      method: 'GET',
      headers,
      // Routing is static-ish; let Next cache for 60s to avoid hammering the
      // Python service on every Settings page navigation.
      next: { revalidate: 60 },
    })

    if (!resp.ok) {
      return jsonResponse({
        backend_online: false,
        capabilities: [],
        emergency_fallbacks: [],
      })
    }

    const data = await resp.json()
    return jsonResponse({ backend_online: true, ...data })
  } catch {
    // Python service down — surface it cleanly rather than 500ing the page
    return jsonResponse({
      backend_online: false,
      capabilities: [],
      emergency_fallbacks: [],
    })
  }
}
