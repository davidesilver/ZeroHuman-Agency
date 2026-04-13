/**
 * API helper utilities for Next.js route handlers.
 *
 * H-02: proxyToBackend now forwards the user's Supabase JWT to the Python
 * backend in the Authorization header. This is required for C-01/C-02
 * authentication to work end-to-end.
 *
 * L-07: A unique X-Request-ID is generated per request and propagated to
 * the backend to enable correlated logging across the full request chain.
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000'

/**
 * Proxy a request to the Python backend, forwarding the user's JWT.
 *
 * H-02: The Authorization header is populated from the current Supabase
 * session so the FastAPI JWTAuthMiddleware can verify the caller.
 *
 * L-07: X-Request-ID is generated here and propagated to the backend.
 * The backend reflects it in the response header for end-to-end correlation.
 */
export async function proxyToBackend(
  path: string,
  options: { method?: string; body?: unknown } = {}
) {
  const { method = 'GET', body } = options

  // L-07: Generate a unique request ID for distributed tracing
  const requestId = crypto.randomUUID()

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
    'X-Request-ID': requestId,  // L-07: correlation ID
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
  const response = NextResponse.json(data, { status: resp.status })
  
  // L-07: Reflect backend's X-Request-ID in the response to the browser
  const backendRequestId = resp.headers.get('X-Request-ID')
  if (backendRequestId) {
    response.headers.set('X-Request-ID', backendRequestId)
  }

  return response
}

export function jsonResponse(data: unknown, status = 200) {
  return NextResponse.json({ success: true, data }, { status })
}

export function errorResponse(message: string, status = 400) {
  return NextResponse.json({ success: false, error: { message } }, { status })
}
