import { proxyToBackend } from '@/lib/api-helpers'

export async function POST() {
  return proxyToBackend('/api/analytics/feedback-loop', { method: 'POST' })
}
