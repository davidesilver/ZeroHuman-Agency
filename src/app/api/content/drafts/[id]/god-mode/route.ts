import { proxyToBackend } from '@/lib/api-helpers'

export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return proxyToBackend(`/api/content/drafts/${id}/god-mode`, { method: 'POST' })
}
