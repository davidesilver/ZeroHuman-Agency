// src/app/api/brands/[id]/assets/route.ts
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import type { Json } from '@/lib/types/database.types'

interface Ctx { params: Promise<{ id: string }> }

const VALID_KINDS = new Set([
  'logo_primary','logo_mono','logo_favicon',
  'palette','font_specimen','design_system_pdf',
  'example_newsletter','example_post','example_carousel',
  'watermark','other',
])

export async function GET(_: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('brand_assets')
    .select('id,kind,label,storage_path,mime_type,bytes,width_px,height_px,palette_hex,metadata,created_at')
    .eq('brand_id', brandId)
    .order('kind')
    .order('created_at', { ascending: false })
  if (error) return errorResponse(error.message, 500)
  return jsonResponse(data || [])
}

/** Called *after* the browser finishes uploading to Storage. Registers metadata. */
export async function POST(req: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  let body: {
    kind?: string; label?: string; storage_path?: string; mime_type?: string;
    bytes?: number; width_px?: number; height_px?: number;
    palette_hex?: string[]; metadata?: Record<string, unknown>;
  }
  try { body = await req.json() } catch { return errorResponse('Invalid JSON', 400) }
  if (!body.kind || !VALID_KINDS.has(body.kind)) return errorResponse('Invalid kind', 400)
  if (!body.storage_path || !body.storage_path.startsWith(`${brandId}/`))
    return errorResponse('storage_path must begin with the brand id', 400)
  if (!body.mime_type || !body.bytes) return errorResponse('mime_type and bytes required', 400)

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('brand_assets')
    .insert({
      brand_id: brandId,
      kind: body.kind,
      label: body.label ?? null,
      storage_path: body.storage_path,
      mime_type: body.mime_type,
      bytes: body.bytes,
      width_px: body.width_px ?? null,
      height_px: body.height_px ?? null,
      palette_hex: body.palette_hex ?? null,
      metadata: (body.metadata ?? {}) as Json,
      uploaded_by: auth.userId,
    })
    .select('id,kind,label,storage_path,mime_type,bytes,palette_hex,metadata,created_at')
    .single()
  if (error) return errorResponse(error.message, 500)
  return jsonResponse(data, 201)
}
