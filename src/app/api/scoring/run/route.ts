import { proxyToBackend } from '@/lib/api-helpers'

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}))
  return proxyToBackend('/api/scoring/run', { method: 'POST', body })
}
