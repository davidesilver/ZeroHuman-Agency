import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000'

// Brevo sends JSON; forward raw body to Python without auth (provider-to-server call)
export async function POST(request: NextRequest) {
  try {
    const body = await request.text()
    const resp = await fetch(`${BACKEND}/api/webhooks/email/brevo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
    const data = await resp.json()
    return NextResponse.json(data, { status: resp.status })
  } catch {
    return NextResponse.json({ ok: false }, { status: 500 })
  }
}
