import { NextRequest } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'

export async function POST(request: NextRequest) {
  let body = {}
  try {
    body = await request.json()
  } catch {
    // Empty body is ok — backend uses defaults
  }
  return proxyToBackend('/api/newsletter/generate', {
    method: 'POST',
    body,
  })
}
