/**
 * API helper utilities for Next.js route handlers.
 *
 * H-02: proxyToBackend now forwards the user's Supabase JWT to the Python
 * backend in the Authorization header. This is required for C-01/C-02
 * authentication to work end-to-end.
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000'

/**
 * Proxy a request to the Python backend, forwarding the user's JWT.
 *
 * H-02: The Authorization header is populated from the current Supabase
 * session so the FastAPI JWTAuthMiddleware can verify the caller.
 */
export async function proxyToBackend(
  path: string,
  options: { method?: string; body?: unknown } = {}
) {
  const { method = 'GET', body } = options

  // H-02: Retrieve the current session token from Supabase
  let authHeader: string | undefined
  try {
    const supabase = await createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.access_token) {
      authHeader = `Bearer ${session.access_token}`
    }
  } catch {
    // Non-fatal — backend will reject with 401 if token is missing
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (authHeader) {
    headers['Authorization'] = authHeader
  }

  const resp = await fetch(`${PYTHON_BACKEND_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  const data = await resp.json()
  return NextResponse.json(data, { status: resp.status })
}

export function jsonResponse(data: unknown, status = 200) {
  return NextResponse.json({ success: true, data }, { status })
}

export function errorResponse(message: string, status = 400) {
  return NextResponse.json({ success: false, error: { message } }, { status })
}
