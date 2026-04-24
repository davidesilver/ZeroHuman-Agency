/**
 * PATCH  /api/memory/facts/[id]  — edit statement / tier / importance
 * DELETE /api/memory/facts/[id]  — hard delete
 *
 * Both proxy to the Python backend which handles embedding re-generation
 * and ownership verification.
 */
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { proxyToBackend } from '@/lib/api-helpers'
import { NextRequest } from 'next/server'

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { id } = await params
  const body = await request.json()
  return proxyToBackend(`/api/memory/facts/${id}`, { method: 'PATCH', body })
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { id } = await params
  return proxyToBackend(`/api/memory/facts/${id}`, { method: 'DELETE' })
}
