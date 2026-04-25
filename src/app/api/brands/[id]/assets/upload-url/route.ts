/**
 * Issues a short-lived signed upload URL for the brand-assets bucket.
 * The browser PUTs the file directly to Supabase Storage — server never holds bytes.
 * Path convention: "<brand_id>/<uuid>.<ext>" so RLS policy split_part() works.
 */
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { randomUUID } from 'crypto'

interface Ctx { params: Promise<{ id: string }> }

const ALLOWED_MIME = new Set([
  'image/png','image/jpeg','image/svg+xml','image/webp',
  'application/pdf',
])
const MAX_BYTES = 15 * 1024 * 1024 // 15 MB

export async function POST(req: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  let body: { filename?: string; mime_type?: string; bytes?: number }
  try { body = await req.json() } catch { return errorResponse('Invalid JSON', 400) }

  if (!body.mime_type || !ALLOWED_MIME.has(body.mime_type))
    return errorResponse(`mime_type must be one of: ${[...ALLOWED_MIME].join(', ')}`, 400)
  if (!body.bytes || body.bytes <= 0 || body.bytes > MAX_BYTES)
    return errorResponse(`bytes must be 1..${MAX_BYTES}`, 400)

  const ext = (body.filename || '').split('.').pop()?.toLowerCase().replace(/[^a-z0-9]/g,'') || 'bin'
  const path = `${brandId}/${randomUUID()}.${ext}`

  const supabase = await createClient()
  const { data, error } = await supabase
    .storage
    .from('brand-assets')
    .createSignedUploadUrl(path)
  if (error) return errorResponse(error.message, 500)

  return jsonResponse({
    upload_url: data.signedUrl,
    token: data.token,
    storage_path: path,
    expires_in_seconds: 60,
  })
}
