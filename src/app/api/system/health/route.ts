import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'

import { requireAuth } from '@/lib/supabase/auth-helpers'
import { NextRequest } from 'next/server'

interface AgentHealth {
  id: string
  brand_id: string
  agent_name: string
  status: 'healthy' | 'degraded' | 'down'
  last_seen: string
  current_model: string
  fallback_model: string | null
  engine: 'anthropic' | 'openrouter' | 'unknown'
  last_latency_ms: number | null
  uptime_pct: number
  errors_today: number
  queue_size: number
}

interface HealthSummary {
  agents_healthy: number
  agents_degraded: number
  agents_down: number
  avg_uptime: number
  total_errors: number
  total_queue: number
  active_models: string[]
  active_engines: string[]
  emergency_fallbacks_24h: number
}

export async function GET(request: NextRequest) {
  try {
    const { auth, response } = await requireAuth()
    if (!auth) return response

    const supabase = await createClient()

    // Fetch agent health with new LLM metadata
    const { data: agents, error } = await supabase
      .from('pipeline_health')
      .select('*')
      .eq('brand_id', auth.brandId)
      .order('agent_name')

    if (error) return errorResponse(error.message, 500)

    const typedAgents: AgentHealth[] = agents || []

    // Calculate aggregate metrics
    const avgUptime = typedAgents.length > 0
      ? typedAgents.reduce((sum, a) => sum + (a.uptime_pct || 0), 0) / typedAgents.length
      : 0
    const totalErrors = typedAgents.reduce((sum, a) => sum + (a.errors_today || 0), 0)
    const totalQueue = typedAgents.reduce((sum, a) => sum + (a.queue_size || 0), 0)

    // Extract unique active models and engines
    const activeModels = [...new Set(
      typedAgents.map(a => a.current_model).filter(Boolean)
    )]
    const activeEngines = [...new Set(
      typedAgents.map(a => a.engine).filter(Boolean)
    )]

    // Count emergency fallbacks in last 24h
    const { data: fallbacks } = await supabase
      .from('llm_fallback_log')
      .select('*')
      .eq('brand_id', auth.brandId)
      .eq('is_emergency', true)
      .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())

    const emergencyCount = fallbacks?.length || 0

    const summary: HealthSummary = {
      avg_uptime: Math.round(avgUptime * 10) / 10,
      total_errors: totalErrors,
      total_queue: totalQueue,
      agents_healthy: typedAgents.filter(a => a.status === 'healthy').length,
      agents_degraded: typedAgents.filter(a => a.status === 'degraded').length,
      agents_down: typedAgents.filter(a => a.status === 'down').length,
      active_models: activeModels,
      active_engines: activeEngines,
      emergency_fallbacks_24h: emergencyCount,
    }

    return jsonResponse({
      agents: typedAgents,
      summary,
    })
  } catch (err) {
    return errorResponse('Failed to fetch health data', 500)
  }
}
