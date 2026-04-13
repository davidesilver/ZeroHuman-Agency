import { NextRequest } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'

export async function POST(request: NextRequest) {
  return proxyToBackend('/api/social/publish/twitter', {
    method: 'POST',
    body: await request.json(),
  })
}
