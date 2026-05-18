import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000'

// Forward Telegram Bot API webhook updates to Python backend.
// Auth is validated by the Python handler via X-Telegram-Bot-Api-Secret-Token.
export async function POST(request: NextRequest) {
  try {
    const body = await request.text()
    const secret = request.headers.get('x-telegram-bot-api-secret-token') ?? ''
    const resp = await fetch(`${BACKEND}/api/webhooks/telegram`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Bot-Api-Secret-Token': secret,
      },
      body,
    })
    const data = await resp.json()
    return NextResponse.json(data, { status: resp.status })
  } catch {
    return NextResponse.json({ ok: false }, { status: 500 })
  }
}
