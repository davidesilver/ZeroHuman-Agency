// src/app/api/brands/[id]/assets/[assetId]/route.ts
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { Database } from '@/lib/types/database.types'

interface Ctx { params: Promise<{ id: string; assetId: string }> }

export async function DELETE(_: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId, assetId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  const supabase = await createClient()
  const { data: row, error: selErr } = await supabase
    .from('brand_assets')
    .select('storage_path')
    .eq('id', assetId)
    .eq('brand_id', brandId)
    .single()
  if (selErr || !row) return errorResponse('Asset not found', 404)

  const storagePath = (row as Database['public']['Tables']['brand_assets']['Row']).storage_path
  // Delete the file first; if this fails we keep the DB row so we can retry.
  const { error: storageErr } = await supabase.storage.from('brand-assets').remove([storagePath])
  if (storageErr) return errorResponse(`Storage delete failed: ${storageErr.message}`, 500)

  const { error: delErr } = await supabase.from('brand_assets').delete().eq('id', assetId)
  if (delErr) return errorResponse(delErr.message, 500)
  return jsonResponse({ deleted: assetId })
}

export async function PATCH(req: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId, assetId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  let body: { label?: string; palette_hex?: string[]; metadata?: Record<string, unknown> }
  try { body = await req.json() } catch { return errorResponse('Invalid JSON', 400) }

  type Patch = Database['public']['Tables']['brand_assets']['Update']
  const patch: Partial<Patch> = {}
  if (body.label !== undefined) patch.label = String(body.label).slice(0, 120)
  if (body.palette_hex !== undefined) {
    if (!Array.isArray(body.palette_hex) || body.palette_hex.some(s => !/^#[0-9a-f]{6}$/i.test(s)))
      return errorResponse('palette_hex must be ["#rrggbb", ...]', 400)
    patch.palette_hex = body.palette_hex
  }
  if (body.metadata !== undefined) patch.metadata = body.metadata as Database['public']['Tables']['brand_assets']['Update']['metadata']
  if (Object.keys(patch).length === 0) return errorResponse('No editable fields', 400)

  const supabase = await createClient()
  const { data, error } = await supabase.from('brand_assets')
    .update(patch).eq('id', assetId).eq('brand_id', brandId)
    .select().single()
  if (error) return errorResponse(error.message, 500)
  return jsonResponse(data)
}
