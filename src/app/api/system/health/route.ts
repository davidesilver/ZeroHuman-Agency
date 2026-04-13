import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'

const BRAND_ID = 'b6e639ac-33e7-402b-b928-c98af55eec47'

export async function GET() {
  try {
    const supabase = await createClient()

    const { data: health, error } = await supabase
      .from('pipeline_health')
      .select('*')
      .eq('brand_id', BRAND_ID)
      .order('agent_name')

    if (error) return errorResponse(error.message, 500)

    // Calculate aggregate metrics
    const agents = health || []
    const avgUptime = agents.length > 0
      ? agents.reduce((sum, a) => sum + (a.uptime_pct || 0), 0) / agents.length
      : 0
    const totalErrors = agents.reduce((sum, a) => sum + (a.errors_today || 0), 0)
    const totalQueue = agents.reduce((sum, a) => sum + (a.queue_size || 0), 0)

    return jsonResponse({
      agents,
      summary: {
        avg_uptime: Math.round(avgUptime * 10) / 10,
        total_errors: totalErrors,
        total_queue: totalQueue,
        agents_healthy: agents.filter(a => a.status === 'healthy').length,
        agents_degraded: agents.filter(a => a.status === 'degraded').length,
        agents_down: agents.filter(a => a.status === 'down').length,
      },
    })
  } catch (err) {
    return errorResponse('Failed to fetch health data', 500)
  }
}
