import { proxyToBackend } from '@/lib/api-helpers'

/** Brevo webhook — no auth, verified by HMAC in the backend */
export async function POST(request: Request) {
  try {
    const body = await request.json()
    return proxyToBackend('/email-marketing/campaigns/webhook', { method: 'POST', body })
  } catch {
    return new Response('ok', { status: 200 })
  }
}
