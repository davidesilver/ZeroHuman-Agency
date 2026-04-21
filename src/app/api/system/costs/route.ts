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
    const period = params.get('period') || 'today'

    const now = new Date()
    let since: string

    switch (period) {
      case 'week':
        since = new Date(now.getTime() - 7 * 86400000).toISOString()
        break
      case 'month':
        since = new Date(now.getTime() - 30 * 86400000).toISOString()
        break
      default: // today
        since = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString()
    }

    const { data: costs, error } = await supabase
      .from('api_costs')
      .select('*')
      .eq('brand_id', auth.brandId)
      .gte('created_at', since)
      .order('created_at', { ascending: false })

    if (error) return errorResponse(error.message, 500)

    // Aggregate by agent
    const byAgent: Record<string, {
      agent_name: string
      model: string
      calls: number
      tokens_input: number
      tokens_output: number
      cost_usd: number
    }> = {}

    let totalCost = 0

    for (const c of costs || []) {
      totalCost += Number(c.cost_usd)
      if (!byAgent[c.agent_name]) {
        byAgent[c.agent_name] = {
          agent_name: c.agent_name,
          model: c.model,
          calls: 0,
          tokens_input: 0,
          tokens_output: 0,
          cost_usd: 0,
        }
      }
      byAgent[c.agent_name].calls++
      byAgent[c.agent_name].tokens_input += c.tokens_input || 0
      byAgent[c.agent_name].tokens_output += c.tokens_output || 0
      byAgent[c.agent_name].cost_usd += Number(c.cost_usd)
    }

    // Get totals for all three periods
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString()
    const weekStart = new Date(now.getTime() - 7 * 86400000).toISOString()
    const monthStart = new Date(now.getTime() - 30 * 86400000).toISOString()

    const [todayRes, weekRes, monthRes] = await Promise.all([
      supabase.from('api_costs').select('cost_usd').eq('brand_id', auth.brandId).gte('created_at', todayStart),
      supabase.from('api_costs').select('cost_usd').eq('brand_id', auth.brandId).gte('created_at', weekStart),
      supabase.from('api_costs').select('cost_usd').eq('brand_id', auth.brandId).gte('created_at', monthStart),
    ])

    const sumCosts = (rows: { cost_usd: number }[] | null) =>
      (rows || []).reduce((sum, r) => sum + Number(r.cost_usd), 0)

    return jsonResponse({
      period,
      total_cost: totalCost,
      spend_today: sumCosts(todayRes.data),
      spend_week: sumCosts(weekRes.data),
      spend_month: sumCosts(monthRes.data),
      by_agent: Object.values(byAgent),
      daily_budget: 15.0,
    })
  } catch {
    return errorResponse('Failed to fetch costs', 500)
  }
}
