import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000'

// Mailchimp sends form-encoded data; forward raw body to Python
export async function POST(request: NextRequest) {
  try {
    const body = await request.text()
    const resp = await fetch(`${BACKEND}/api/webhooks/email/mailchimp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
    const data = await resp.json()
    return NextResponse.json(data, { status: resp.status })
  } catch {
    return NextResponse.json({ ok: false }, { status: 500 })
  }
}

// Mailchimp performs a GET to verify the webhook URL before activating it
export async function GET() {
  return new NextResponse(null, { status: 200 })
}
