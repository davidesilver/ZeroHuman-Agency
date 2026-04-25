import { Suspense } from 'react'

import { Activity } from 'lucide-react'

import { KPICard } from '@/components/dashboard/kpi-card'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

import {
  loadActivity,
  loadCosts,
  loadHealth,
  loadStats,
} from './_dashboard-data'

export const dynamic = 'force-dynamic'

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>

      <Suspense fallback={<KpiRowSkeleton count={4} />}>
        <PrimaryKpis />
      </Suspense>

      <Suspense fallback={<KpiRowSkeleton count={3} />}>
        <HealthKpis />
      </Suspense>

      <Suspense fallback={<KpiRowSkeleton count={3} />}>
        <LlmKpis />
      </Suspense>

      <Suspense fallback={<PipelineSkeleton />}>
        <PipelineCard />
      </Suspense>

      <div className="grid grid-cols-2 gap-4">
        <Suspense fallback={<TableSkeleton title="Recent Activity" />}>
          <ActivityCard />
        </Suspense>
        <Suspense fallback={<TableSkeleton title="Agent Status" />}>
          <AgentStatusCard />
        </Suspense>
      </div>
    </div>
  )
}

// ── Sections ──────────────────────────────────────────────────────────────

async function PrimaryKpis() {
  const [stats, costs, health] = await Promise.all([
    loadStats(),
    loadCosts(),
    loadHealth(),
  ])
  const totalPipeline = stats.new + stats.scored + stats.approved
  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      <KPICard title="Content in pipeline" value={totalPipeline} />
      <KPICard title="Published" value={stats.published} />
      <KPICard
        title="Active agents"
        value={`${health.summary.agents_healthy} / ${health.agents.length || 5}`}
      />
      <KPICard
        title="API spend today"
        value={`$${costs.spend_today.toFixed(2)}`}
        subtitle={
          costs.daily_budget !== null
            ? `Budget $${costs.daily_budget.toFixed(2)}`
            : undefined
        }
        variant={
          costs.daily_budget !== null && costs.spend_today >= costs.daily_budget
            ? 'destructive'
            : 'default'
        }
      />
    </div>
  )
}

async function HealthKpis() {
  const { summary } = await loadHealth()
  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      <KPICard
        title="Avg Uptime"
        value={`${summary.avg_uptime}%`}
        subtitle={summary.avg_uptime < 95 ? 'Degraded' : 'Excellent'}
        variant={summary.avg_uptime < 95 ? 'destructive' : 'default'}
      />
      <KPICard
        title="Total Pipeline Errors"
        value={summary.total_errors}
        subtitle={
          summary.total_errors > 0 ? 'Action required' : 'System healthy'
        }
        variant={summary.total_errors > 0 ? 'destructive' : 'default'}
      />
      <KPICard
        title="Total Tasks in Queue"
        value={summary.total_queue}
        subtitle={summary.total_queue > 50 ? 'High load' : 'Normal queue'}
      />
    </div>
  )
}

async function LlmKpis() {
  const { summary } = await loadHealth()
  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      <KPICard
        title="Active LLM Models"
        value={summary.active_models.length}
        subtitle={
          summary.active_models.slice(0, 2).join(', ') +
          (summary.active_models.length > 2 ? '…' : '')
        }
      />
      <KPICard
        title="Engines Active"
        value={summary.active_engines.length}
        subtitle={summary.active_engines.join(', ')}
      />
      <KPICard
        title="Emergency Fallbacks (24h)"
        value={summary.emergency_fallbacks_24h}
        subtitle={
          summary.emergency_fallbacks_24h > 0 ? 'Alert' : 'Normal'
        }
        variant={
          summary.emergency_fallbacks_24h > 0 ? 'destructive' : 'default'
        }
      />
    </div>
  )
}

async function PipelineCard() {
  const stats = await loadStats()
  const stages = [
    { label: 'Discovery', count: stats.new },
    { label: 'Scored', count: stats.scored },
    { label: 'Approved', count: stats.approved },
    { label: 'Published', count: stats.published },
  ]
  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="text-base">Content Pipeline</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          {stages.map((stage, i) => (
            <div key={stage.label} className="flex items-center">
              <div className="text-center">
                <p className="text-2xl font-bold">{stage.count}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {stage.label}
                </p>
              </div>
              {i < stages.length - 1 && (
                <span className="mx-3 text-muted-foreground">→</span>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

async function ActivityCard() {
  const activities = await loadActivity(10)
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {activities.length === 0 ? (
          <p className="text-center text-sm text-muted-foreground py-8">
            No activity — system not yet active
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
              {activities.map((a) => (
                <TableRow key={`${a.type}-${a.timestamp}-${a.message}`}>
                  <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                    {a.timestamp
                      ? new Date(a.timestamp).toLocaleTimeString('en-US', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : '—'}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px]">
                      {a.type.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">{a.message}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

async function AgentStatusCard() {
  const { agents } = await loadHealth()
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Agent Status</CardTitle>
      </CardHeader>
      <CardContent>
        {agents.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Activity className="size-8 mx-auto mb-3 opacity-40" />
            <p className="text-sm">No agent activity yet</p>
            <p className="text-xs mt-1">
              Generate content to see real-time agent status
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {agents.map((a) => {
              const isUsingFallback = a.fallback_model !== null
              const latencyColor =
                a.last_latency_ms && a.last_latency_ms > 5000
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
                        variant={
                          a.status === 'healthy' ? 'default' : 'secondary'
                        }
                        className="text-xs"
                      >
                        {a.status === 'healthy'
                          ? 'Online'
                          : a.status === 'degraded'
                          ? 'Degraded'
                          : 'Offline'}
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
                    Engine:{' '}
                    <span className="font-medium">{a.engine || 'Unknown'}</span>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

// ── Skeletons ─────────────────────────────────────────────────────────────

function KpiRowSkeleton({ count }: { count: number }) {
  return (
    <div
      className="grid gap-4 mb-6"
      style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className="h-28 rounded-lg" />
      ))}
    </div>
  )
}

function PipelineSkeleton() {
  return <Skeleton className="h-32 mb-6 rounded-lg" />
}

function TableSkeleton({ title }: { title: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-full" />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
