/**
 * POST /api/memory/upload — upload a document and extract candidate memory facts (preview)
 *
 * P3.3: Proxies multipart form upload to Python backend /api/memory/upload-source.
 * Nothing is persisted — returns candidates for UI review.
 * User calls /api/memory/consolidate to persist selected facts.
 *
 * Accepted file types: .txt, .md, .pdf, .docx
 */
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const supabase = await createClient()
  const { data: { session } } = await supabase.auth.getSession()

  // Forward multipart form as-is, injecting brand_id
  const formData = await request.formData()
  if (!formData.has('brand_id')) {
    formData.append('brand_id', auth.activeBrandId)
  }

  const headers: Record<string, string> = {}
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }

  const resp = await fetch(`${PYTHON_BACKEND_URL}/api/memory/upload-source`, {
    method: 'POST',
    headers,
    body: formData,
  })

  const data = await resp.json()
  return NextResponse.json(data, { status: resp.status })
}
