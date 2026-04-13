import { NextRequest } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'

export async function POST(request: NextRequest) {
  return proxyToBackend('/api/newsletter/send', {
    method: 'POST',
    body: await request.json(),
  })
}
