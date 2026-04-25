import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

interface Ctx { params: Promise<{ id: string; assetId: string }> }

export async function GET(_: Request, ctx: Ctx) {
  const { auth, response } = await requireAuth()
  if (!auth) return response
  const { id: brandId, assetId } = await ctx.params
  if (!auth.memberBrandIds.includes(brandId)) return errorResponse('Forbidden', 403)

  const supabase = await createClient()
  const { data: row, error } = await supabase
    .from('brand_assets')
    .select('storage_path').eq('id', assetId).eq('brand_id', brandId).single()
  if (error || !row) return errorResponse('Not found', 404)

  const storagePath = row.storage_path
  if (!storagePath) return errorResponse('Not found', 404)

  const { data, error: sigErr } = await supabase.storage.from('brand-assets')
    .createSignedUrl(storagePath, 60 * 10) // 10 min
  if (sigErr) return errorResponse(sigErr.message, 500)
  return jsonResponse({ url: data.signedUrl })
}
