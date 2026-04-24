import { NextRequest } from 'next/server'
import { proxyToBackend } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function POST(request: NextRequest) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  // routes.py mounts schedule at /social/schedule (no /api prefix)
  return proxyToBackend('/social/schedule', {
    method: 'POST',
    body: await request.json(),
  })
}
