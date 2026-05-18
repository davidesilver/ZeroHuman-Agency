import { NextRequest } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'

export async function GET(request: NextRequest) {
  return proxyToBackend('/api/email-provider/config', { method: 'GET' })
}

export async function POST(request: NextRequest) {
  const body = await request.json()
  return proxyToBackend('/api/email-provider/config', { method: 'POST', body })
}
