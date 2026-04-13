'use client'

import { useCallback, useEffect, useState } from 'react'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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
  const [health, setHealth] = useState<{ agents: { agent_name: string; status: string; uptime_pct: number | null }[]; summary: { agents_healthy: number; agents_down: number; agents_degraded: number } }>({ agents: [], summary: { agents_healthy: 0, agents_down: 0, agents_degraded: 0 } })

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
              <ul className="space-y-3">
                {['ResearchBot', 'ScoringAgent', 'WriterAgent', 'EditorAgent', 'FactChecker'].map(name => (
                  <li key={name} className="flex items-center justify-between">
                    <span className="text-sm font-medium">{name}</span>
                    <Badge variant="secondary" className="text-xs">Offline</Badge>
                  </li>
                ))}
              </ul>
            ) : (
              <ul className="space-y-3">
                {health.agents.map(a => (
                  <li key={a.agent_name} className="flex items-center justify-between">
                    <span className="text-sm font-medium">{a.agent_name}</span>
                    <Badge
                      variant={a.status === 'healthy' ? 'default' : 'secondary'}
                      className="text-xs"
                    >
                      {a.status === 'healthy' ? 'Online' : a.status === 'degraded' ? 'Degraded' : 'Offline'}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
