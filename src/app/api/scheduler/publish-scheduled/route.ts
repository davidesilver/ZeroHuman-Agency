import { proxyToBackend } from '@/lib/api-helpers'

export async function POST() {
  return proxyToBackend('/api/scheduler/publish-scheduled', { method: 'POST' })
}
