/**
 * Server-side data loaders for the dashboard.
 *
 * Each loader is wrapped in React.cache so when multiple Suspense boundaries
 * pull the same data inside one render they share the round-trip.  All queries
 * are scoped to the active brand via requireAuth().
 */
import { cache } from 'react'

import { createClient } from '@/lib/supabase/server'
import { requireAuth } from '@/lib/supabase/auth-helpers'

export interface AgentHealthRow {
  agent_name: string
  status: 'healthy' | 'degraded' | 'down' | string
  uptime_pct: number | null
  current_model: string | null
  fallback_model: string | null
  engine: string | null
  last_latency_ms: number | null
  errors_today: number | null
  queue_size: number | null
}

export interface DashboardHealth {
  agents: AgentHealthRow[]
  summary: {
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
}

export interface DashboardStats {
  new: number
  scored: number
  approved: number
  published: number
}

export interface DashboardCosts {
  spend_today: number
  daily_budget: number | null
}

export interface DashboardActivity {
  type: string
  message: string
  timestamp: string
  severity?: 'info' | 'success' | 'warning' | 'error'
  entityType?: string | null
  entityId?: string | null
}

export const loadStats = cache(async (): Promise<DashboardStats> => {
  const { auth } = await requireAuth()
  if (!auth) return { new: 0, scored: 0, approved: 0, published: 0 }

  const supabase = await createClient()
  const { data } = await supabase.rpc('research_items_status_counts', {
    p_brand_id: auth.brandId,
  })

  const counts = (data ?? {}) as unknown as Record<string, number>
  return {
    new: counts.pending ?? 0,
    scored: counts.approved ?? 0,
    approved: counts.approved ?? 0,
    published: 0, // TODO: populate from social_metrics once that aggregator lands
  }
})

export const loadCosts = cache(async (): Promise<DashboardCosts> => {
  const { auth } = await requireAuth()
  if (!auth) return { spend_today: 0, daily_budget: null }

  const supabase = await createClient()
  const since = new Date()
  since.setHours(0, 0, 0, 0)

  const [{ data: costs }, { data: brand }] = await Promise.all([
    supabase
      .from('api_costs')
      .select('cost_usd')
      .eq('brand_id', auth.brandId)
      .gte('created_at', since.toISOString()),
    supabase
      .from('brands')
      .select('daily_budget_usd')
      .eq('id', auth.brandId)
      .maybeSingle(),
  ])

  const spend = (costs ?? []).reduce<number>(
    (sum, row) => sum + Number(row.cost_usd ?? 0),
    0
  )

  return {
    spend_today: Number(spend.toFixed(4)),
    daily_budget: (brand?.daily_budget_usd as number | null) ?? null,
  }
})

export const loadActivity = cache(
  async (limit = 50): Promise<DashboardActivity[]> => {
    const { auth } = await requireAuth()
    if (!auth) return []

    const supabase = await createClient()

    // Primary source: notification_events (populated by NotificationService)
    const { data: notifEvents } = await supabase
      .from('notification_events')
      .select('event_type, severity, title, entity_type, entity_id, created_at')
      .eq('brand_id', auth.brandId)
      .neq('event_type', 'daily_digest_sent')
      .order('created_at', { ascending: false })
      .limit(limit)

    if (notifEvents && notifEvents.length > 0) {
      return notifEvents.map((e) => ({
        type: e.event_type as string,
        message: e.title as string,
        timestamp: e.created_at as string,
        severity: (e.severity as DashboardActivity['severity']) ?? 'info',
        entityType: e.entity_type as string | null,
        entityId: e.entity_id as string | null,
      }))
    }

    // Fallback: legacy sources when notification_events is empty
    const [{ data: runs }, { data: drafts }] = await Promise.all([
      supabase
        .from('research_runs')
        .select('id, status, items_found, started_at')
        .eq('brand_id', auth.brandId)
        .order('started_at', { ascending: false })
        .limit(limit),
      supabase
        .from('content_drafts')
        .select('id, title, platform, status, updated_at')
        .eq('brand_id', auth.brandId)
        .order('updated_at', { ascending: false })
        .limit(limit),
    ])

    const events: DashboardActivity[] = []
    for (const r of runs ?? []) {
      events.push({
        type: 'research',
        message: `Research run ${r.status} — ${r.items_found ?? 0} items`,
        timestamp: r.started_at as string,
        severity: 'info',
      })
    }
    for (const d of drafts ?? []) {
      events.push({
        type: 'draft',
        message: `${d.platform ?? 'draft'} · ${d.title ?? '(untitled)'} → ${d.status}`,
        timestamp: d.updated_at as string,
        severity: 'info',
      })
    }

    return events
      .filter((e) => Boolean(e.timestamp))
      .sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1))
      .slice(0, limit)
  }
)

export const loadHealth = cache(async (): Promise<DashboardHealth> => {
  const empty: DashboardHealth = {
    agents: [],
    summary: {
      agents_healthy: 0,
      agents_degraded: 0,
      agents_down: 0,
      avg_uptime: 0,
      total_errors: 0,
      total_queue: 0,
      active_models: [],
      active_engines: [],
      emergency_fallbacks_24h: 0,
    },
  }

  const { auth } = await requireAuth()
  if (!auth) return empty

  const supabase = await createClient()

  const { data: rawAgents } = await supabase
    .from('pipeline_health')
    .select(
      'agent_name,status,uptime_pct,current_model,fallback_model,engine,last_latency_ms,errors_today,queue_size'
    )
    .eq('brand_id', auth.brandId)
    .order('agent_name')

  const agents: AgentHealthRow[] = (rawAgents ?? []) as AgentHealthRow[]

  const { count: emergencyCount } = await supabase
    .from('llm_fallback_log')
    .select('id', { count: 'exact', head: true })
    .eq('brand_id', auth.brandId)
    .eq('is_emergency', true)
    .gte(
      'created_at',
      new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
    )

  const avg = agents.length
    ? agents.reduce((s, a) => s + (a.uptime_pct ?? 0), 0) / agents.length
    : 0

  return {
    agents,
    summary: {
      agents_healthy: agents.filter((a) => a.status === 'healthy').length,
      agents_degraded: agents.filter((a) => a.status === 'degraded').length,
      agents_down: agents.filter((a) => a.status === 'down').length,
      avg_uptime: Math.round(avg * 10) / 10,
      total_errors: agents.reduce((s, a) => s + (a.errors_today ?? 0), 0),
      total_queue: agents.reduce((s, a) => s + (a.queue_size ?? 0), 0),
      active_models: [
        ...new Set(
          agents
            .map((a) => a.current_model)
            .filter((m): m is string => Boolean(m))
        ),
      ],
      active_engines: [
        ...new Set(
          agents.map((a) => a.engine).filter((e): e is string => Boolean(e))
        ),
      ],
      emergency_fallbacks_24h: emergencyCount ?? 0,
    },
  }
})
