import { proxyToBackend } from '@/lib/api-helpers'

export async function POST() {
  return proxyToBackend('/api/scheduler/daily-pipeline', { method: 'POST' })
}
