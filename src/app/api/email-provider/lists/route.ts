import { NextRequest } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'

export async function GET(request: NextRequest) {
  return proxyToBackend('/api/email-provider/lists', { method: 'GET' })
}
