import { NextResponse } from 'next/server'

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000'

export async function proxyToBackend(
  path: string,
  options: { method?: string; body?: unknown } = {}
) {
  const { method = 'GET', body } = options
  const resp = await fetch(`${PYTHON_BACKEND_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
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
