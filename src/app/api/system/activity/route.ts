import { NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'

import { requireAuth } from '@/lib/supabase/auth-helpers'

export async function GET(request: NextRequest) {
  try {
    const { auth, response } = await requireAuth()
    if (!auth) return response

    const supabase = await createClient()
    const params = request.nextUrl.searchParams
    const limit = parseInt(params.get('limit') || '20', 10)

    // Build activity feed from recent research runs, drafts, and newsletters
    const [runsRes, draftsRes, newslettersRes] = await Promise.all([
      supabase
        .from('research_runs')
        .select('id, status, items_found, sources_scanned, started_at')
        .eq('brand_id', auth.brandId)
        .order('started_at', { ascending: false })
        .limit(10),
      supabase
        .from('content_drafts')
        .select('id, title, content_type, platform, status, created_at, updated_at')
        .eq('brand_id', auth.brandId)
        .order('updated_at', { ascending: false })
        .limit(10),
      supabase
        .from('newsletters')
        .select('id, title, status, created_at')
        .eq('brand_id', auth.brandId)
        .order('created_at', { ascending: false })
        .limit(5),
    ])

    // Merge into unified activity feed
    const activities: {
      type: string
      message: string
      timestamp: string
      id: string
    }[] = []

    for (const run of runsRes.data || []) {
      activities.push({
        type: 'research',
        message: `Research completed: ${run.items_found || 0} items from ${run.sources_scanned || 0} sources`,
        timestamp: run.started_at || '',
        id: run.id,
      })
    }

    for (const draft of draftsRes.data || []) {
      const title = draft.title || 'Untitled'
      const action = draft.status === 'published' ? 'Published' :
                     draft.status === 'approved' ? 'Approved' :
                     draft.status === 'in_review' ? 'In review' :
                     draft.status === 'god_mode' ? 'GOD Mode' : 'Created'
      activities.push({
        type: 'content',
        message: `${action}: "${title}" (${draft.content_type}${draft.platform ? ` / ${draft.platform}` : ''})`,
        timestamp: draft.updated_at || draft.created_at || '',
        id: draft.id,
      })
    }

    for (const nl of newslettersRes.data || []) {
      activities.push({
        type: 'newsletter',
        message: `Newsletter: "${nl.title || 'Untitled'}" — ${nl.status}`,
        timestamp: nl.created_at || '',
        id: nl.id,
      })
    }

    // Sort by timestamp descending and limit
    activities.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

    return jsonResponse({
      activities: activities.slice(0, limit),
      total: activities.length,
    })
  } catch (err) {
    return errorResponse('Failed to fetch activity', 500)
  }
}
