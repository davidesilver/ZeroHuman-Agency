import { NextRequest } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  return proxyToBackend(`/api/newsletter/${id}/report`)
}
