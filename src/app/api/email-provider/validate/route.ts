import { NextRequest } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'

export async function POST(request: NextRequest) {
  const body = await request.json()
  return proxyToBackend('/api/email-provider/validate', { method: 'POST', body })
}
