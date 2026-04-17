'use client'

import { useCallback, useEffect, useState } from 'react'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export default function DashboardPage() {
  const [stats, setStats] = useState({ new: 0, scored: 0, approved: 0, published: 0 })
  const [activities, setActivities] = useState<{ type: string; message: string; timestamp: string }[]>([])
  const [costs, setCosts] = useState({ spend_today: 0, daily_budget: 15 })
  const [health, setHealth] = useState<{
    agents: {
      agent_name: string
      status: string
      uptime_pct: number | null
      current_model: string | null
      fallback_model: string | null
      engine: string | null
      last_latency_ms: number | null
    }[]
    summary: {
      agents_healthy: number
      agents_down: number
      agents_degraded: number
      active_models: string[]
      active_engines: string[]
      emergency_fallbacks_24h: number
    }
  }>({ agents: [], summary: { agents_healthy: 0, agents_down: 0, agents_degraded: 0, active_models: [], active_engines: [], emergency_fallbacks_24h: 0 } })

  const fetchData = useCallback(async () => {
    const [statsRes, activityRes, costsRes, healthRes] = await Promise.all([
      fetch('/api/research/stats').then(r => r.json()).catch(() => null),
      fetch('/api/system/activity?limit=10').then(r => r.json()).catch(() => null),
      fetch('/api/system/costs?period=today').then(r => r.json()).catch(() => null),
      fetch('/api/system/health').then(r => r.json()).catch(() => null),
    ])

    if (statsRes?.success) {
      const d = statsRes.data
      setStats({
        new: d.new || d.pending || 0,
        scored: d.scored || 0,
        approved: d.approved || 0,
        published: d.published || 0,
      })
    }
    if (activityRes?.success) setActivities(activityRes.data.activities || [])
    if (costsRes?.success) setCosts({ spend_today: costsRes.data.spend_today || 0, daily_budget: costsRes.data.daily_budget || 15 })
    if (healthRes?.success) setHealth(healthRes.data)
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const totalPipeline = stats.new + stats.scored + stats.approved

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>

      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPICard title="Content in pipeline" value={totalPipeline} />
        <KPICard title="Published" value={stats.published} />
        <KPICard
          title="Active agents"
          value={`${health.summary.agents_healthy} / ${health.agents.length || 5}`}
        />
        <KPICard title="API spend today" value={`$${costs.spend_today.toFixed(2)}`} />
      </div>

      {/* Agent Health KPI cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <KPICard
          title="Avg Uptime"
          value={`${health.summary.avg_uptime}%`}
          subtitle={health.summary.avg_uptime < 95 ? '⚠️ Degraded' : '✓ Excellent'}
          variant={health.summary.avg_uptime < 95 ? 'destructive' : 'default'}
        />
        <KPICard
          title="Total Pipeline Errors"
          value={health.summary.total_errors}
          subtitle={health.summary.total_errors > 0 ? 'Action required' : 'System healthy'}
          variant={health.summary.total_errors > 0 ? 'destructive' : 'default'}
        />
        <KPICard
          title="Total Tasks in Queue"
          value={health.summary.total_queue}
          subtitle={health.summary.total_queue > 50 ? 'High load' : 'Normal queue'}
        />
      </div>

      {/* LLM Observability KPI cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <KPICard
          title="Active LLM Models"
          value={health.summary.active_models.length}
          subtitle={health.summary.active_models.slice(0, 2).join(', ') + (health.summary.active_models.length > 2 ? '...' : '')}
        />
        <KPICard
          title="Engines Active"
          value={health.summary.active_engines.length}
          subtitle={health.summary.active_engines.join(', ')}
        />
        <KPICard
          title="Emergency Fallbacks (24h)"
          value={health.summary.emergency_fallbacks_24h}
          subtitle={health.summary.emergency_fallbacks_24h > 0 ? '⚠️ Alert!' : '✓ Normal'}
          variant={health.summary.emergency_fallbacks_24h > 0 ? 'destructive' : 'default'}
        />
      </div>

      {/* Pipeline mini */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">Content Pipeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            {[
              { label: 'Discovery', count: stats.new },
              { label: 'Scored', count: stats.scored },
              { label: 'Approved', count: stats.approved },
              { label: 'Published', count: stats.published },
            ].map((stage, i, arr) => (
              <div key={stage.label} className="flex items-center">
                <div className="text-center">
                  <p className="text-2xl font-bold">{stage.count}</p>
                  <p className="text-xs text-muted-foreground mt-1">{stage.label}</p>
                </div>
                {i < arr.length - 1 && <span className="mx-3 text-muted-foreground">&rarr;</span>}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Activity log + Agent status */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            {activities.length === 0 ? (
              <p className="text-center text-sm text-muted-foreground py-8">
                No activity &mdash; system not yet active
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Detail</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {activities.map((a, i) => (
                    <TableRow key={i}>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {a.timestamp ? new Date(a.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : '—'}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-[10px]">{a.type.toUpperCase()}</Badge>
                      </TableCell>
                      <TableCell className="text-sm">{a.message}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Agent Status</CardTitle>
          </CardHeader>
          <CardContent>
            {health.agents.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Activity className="size-8 mx-auto mb-3 opacity-40" />
                <p className="text-sm">No agent activity yet</p>
                <p className="text-xs mt-1">
                  Generate content to see real-time agent status
                </p>
              </div>
            ) : (
              <ul className="space-y-3">
                {health.agents.map(a => {
                  const isUsingFallback = a.fallback_model !== null
                  const latencyColor = a.last_latency_ms && a.last_latency_ms > 5000
                    ? 'text-red-500'
                    : a.last_latency_ms && a.last_latency_ms > 2000
                    ? 'text-yellow-500'
                    : 'text-green-500'

                  return (
                    <li key={a.agent_name} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{a.agent_name}</span>
                        <div className="flex items-center gap-2">
                          <Badge
                            variant={a.status === 'healthy' ? 'default' : 'secondary'}
                            className="text-xs"
                          >
                            {a.status === 'healthy' ? 'Online' : a.status === 'degraded' ? 'Degraded' : 'Offline'}
                          </Badge>
                          {isUsingFallback && (
                            <Badge variant="destructive" className="text-xs">
                              Fallback
                            </Badge>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs text-muted-foreground pl-2">
                        <span>{a.current_model || 'Unknown'}</span>
                        <span className={`font-mono ${latencyColor}`}>
                          {a.last_latency_ms ? `${a.last_latency_ms}ms` : 'N/A'}
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground pl-2">
                        Engine: <span className="font-medium">{a.engine || 'Unknown'}</span>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
