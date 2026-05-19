import { NextResponse } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'

export async function POST(request: Request) {
  const body = await request.json().catch(() => null)
  if (body === null) return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  return proxyToBackend('/api/research/trigger', { method: 'POST', body })
}
