import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'

export async function POST(request: Request) {
  try {
    const { url } = await request.json()

    if (!url || typeof url !== 'string') {
      return errorResponse('URL is required', 400)
    }

    // Validate URL format
    try {
      new URL(url)
    } catch {
      return errorResponse('Invalid URL format', 400)
    }

    const supabase = await createClient()

    // Get the default brand (hardcoded for now, matches Python backend)
    const brandId = 'b6e639ac-33e7-402b-b928-c98af55eec47'

    // Check for duplicate URL
    const { data: existing } = await supabase
      .from('research_items')
      .select('id, title')
      .eq('url', url)
      .eq('brand_id', brandId)
      .limit(1)

    if (existing && existing.length > 0) {
      return errorResponse(`URL already exists: "${existing[0].title}"`, 409)
    }

    // Extract basic info from URL for the research item
    const urlObj = new URL(url)
    const domain = urlObj.hostname.replace('www.', '')

    // Create research item with MANUAL retriever type
    const { data: item, error } = await supabase
      .from('research_items')
      .insert({
        brand_id: brandId,
        retriever_type: 'MANUAL',
        source_type: 'article',
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
  } catch (err) {
    return errorResponse('Failed to process URL', 500)
  }
}
