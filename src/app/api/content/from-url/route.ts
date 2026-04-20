import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  try {
    const { url } = await request.json()

    if (!url || typeof url !== 'string') {
      return errorResponse('URL is required', 400)
    }

    try {
      new URL(url)
    } catch {
      return errorResponse('Invalid URL format', 400)
    }

    const supabase = await createClient()

    const { data: existing } = await supabase
      .from('research_items')
      .select('id, title')
      .eq('url', url)
      .eq('brand_id', auth.brandId)
      .limit(1)

    if (existing && existing.length > 0) {
      return errorResponse(`URL already exists: "${existing[0].title}"`, 409)
    }

    const urlObj = new URL(url)
    const domain = urlObj.hostname.replace('www.', '')

    const { data: item, error } = await supabase
      .from('research_items')
      .insert({
        brand_id: auth.brandId,
        retriever_type: 'manual',
        source_type: 'scrape',
        title: `Manual: ${domain} — ${urlObj.pathname.split('/').filter(Boolean).pop() || 'page'}`,
        url: url,
        source_name: domain,
        summary: `Manually submitted URL from ${domain}. Full content extraction pending.`,
        status: 'new',
        metadata: { submitted_manually: true, submitted_at: new Date().toISOString() },
      })
      .select()
      .single()

    if (error) return errorResponse(error.message, 500)

    return jsonResponse({
      item,
      message: 'URL added to research pipeline. Run scoring to evaluate.',
    })
  } catch {
    return errorResponse('Failed to process URL', 500)
  }
}
