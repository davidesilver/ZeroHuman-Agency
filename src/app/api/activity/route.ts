import { NextRequest } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const limit = searchParams.get('limit') ?? '50'
  const offset = searchParams.get('offset') ?? '0'
  return proxyToBackend(`/api/activity?limit=${limit}&offset=${offset}`)
}
