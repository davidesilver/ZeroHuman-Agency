import { NextRequest } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  return proxyToBackend(`/api/writing-lab/sessions/${id}/vote`, {
    method: 'POST',
    body: await request.json(),
  })
}
