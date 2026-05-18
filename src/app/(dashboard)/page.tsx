import { Suspense } from 'react'
import { Activity } from 'lucide-react'

import { KPICard } from '@/components/dashboard/kpi-card'
import { GettingStartedBanner } from '@/components/dashboard/getting-started'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
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

/**
 * Dashboard — Main overview page.
 *
 * Typography hierarchy (Linear pattern):
 *  - Eyebrow uppercase + tracking → "OVERVIEW"
 *  - Page title h1 (40px / 600 / -1.0px) with coral chip on key word
 *  - Section eyebrows above each KPI row
 *  - Generous 32px gap between sections (Linear rhythm)
 */
export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* ── Page header ──────────────────────────────────────────── */}
      <header className="space-y-2">
        <p className="eyebrow">Overview</p>
        <h1 className="text-ink">
          Welcome to your <span className="chip-coral">Content Engine</span>
        </h1>
        <p className="text-base text-ink-muted max-w-2xl">
          Monitor pipeline health, agent activity, and content velocity across
          every connected brand.
        </p>
      </header>

      <GettingStartedBanner />

      {/* ── Primary KPIs ─────────────────────────────────────────── */}
      <section className="space-y-3">
        <p className="eyebrow">Production</p>
        <Suspense fallback={<KpiRowSkeleton count={4} />}>
          <PrimaryKpis />
        </Suspense>
      </section>

      {/* ── System health ────────────────────────────────────────── */}
      <section className="space-y-3">
        <p className="eyebrow">System Health</p>
        <Suspense fallback={<KpiRowSkeleton count={3} />}>
          <HealthKpis />
        </Suspense>
      </section>

      {/* ── LLM routing ──────────────────────────────────────────── */}
      <section className="space-y-3">
        <p className="eyebrow">LLM Routing</p>
        <Suspense fallback={<KpiRowSkeleton count={3} />}>
          <LlmKpis />
        </Suspense>
      </section>

      {/* ── Pipeline ─────────────────────────────────────────────── */}
      <section className="space-y-3">
        <p className="eyebrow">Pipeline</p>
        <Suspense fallback={<PipelineSkeleton />}>
          <PipelineCard />
        </Suspense>
      </section>

      {/* ── Activity + Agent status (2-up grid) ──────────────────── */}
      <section className="grid grid-cols-2 gap-4">
        <Suspense fallback={<TableSkeleton title="Recent Activity" />}>
          <ActivityCard />
        </Suspense>
        <Suspense fallback={<TableSkeleton title="Agent Status" />}>
          <AgentStatusCard />
        </Suspense>
      </section>
    </div>
  )
}

// ── Sections ────────────────────────────────────────────────────────

async function PrimaryKpis() {
  const [stats, costs, health] = await Promise.all([
    loadStats(),
    loadCosts(),
    loadHealth(),
  ])
  const totalPipeline = stats.new + stats.scored + stats.approved
  return (
    <div className="grid grid-cols-4 gap-4">
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
    <div className="grid grid-cols-3 gap-4">
      <KPICard
        title="Avg Uptime"
        value={`${summary.avg_uptime}%`}
        subtitle={summary.avg_uptime < 95 ? 'Degraded' : 'Excellent'}
        variant={summary.avg_uptime < 95 ? 'destructive' : 'default'}
      />
      <KPICard
        title="Pipeline Errors"
        value={summary.total_errors}
        subtitle={
          summary.total_errors > 0 ? 'Action required' : 'System healthy'
        }
        variant={summary.total_errors > 0 ? 'destructive' : 'default'}
      />
      <KPICard
        title="Tasks in Queue"
        value={summary.total_queue}
        subtitle={summary.total_queue > 50 ? 'High load' : 'Normal queue'}
      />
    </div>
  )
}

async function LlmKpis() {
  const { summary } = await loadHealth()
  return (
    <div className="grid grid-cols-3 gap-4">
      <KPICard
        title="Active models"
        value={summary.active_models.length}
        subtitle={
          summary.active_models.slice(0, 2).join(', ') +
          (summary.active_models.length > 2 ? '…' : '')
        }
      />
      <KPICard
        title="Engines"
        value={summary.active_engines.length}
        subtitle={summary.active_engines.join(', ')}
      />
      <KPICard
        title="Emergency fallbacks (24h)"
        value={summary.emergency_fallbacks_24h}
        subtitle={summary.emergency_fallbacks_24h > 0 ? 'Alert' : 'Normal'}
        variant={summary.emergency_fallbacks_24h > 0 ? 'destructive' : 'default'}
      />
    </div>
  )
}

async function PipelineCard() {
  const stats = await loadStats()
  const stages = [
    { label: 'Discovery', count: stats.new, tint: 'var(--tint-draft)' },
    { label: 'Scored', count: stats.scored, tint: 'var(--tint-review)' },
    { label: 'Approved', count: stats.approved, tint: 'var(--tint-approved)' },
    { label: 'Published', count: stats.published, tint: 'var(--tint-published)' },
  ]
  return (
    <Card>
      <div className="flex items-center justify-between">
        {stages.map((stage, i) => (
          <div key={stage.label} className="flex items-center">
            {/* Notion pastel tint chip per stage */}
            <div
              className="text-center px-5 py-3 rounded-[var(--radius-lg)]"
              style={{ background: stage.tint }}
            >
              <p
                className="tabular font-semibold text-ink"
                style={{
                  fontSize: '28px',
                  letterSpacing: '-0.6px',
                  lineHeight: 1.2,
                }}
              >
                {stage.count}
              </p>
              <p className="eyebrow mt-1 text-[10px]">{stage.label}</p>
            </div>
            {i < stages.length - 1 && (
              <span className="mx-6 text-ink-tertiary text-lg">→</span>
            )}
          </div>
        ))}
      </div>
    </Card>
  )
}

async function ActivityCard() {
  const activities = await loadActivity(10)
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      {activities.length === 0 ? (
        <p className="text-center text-sm text-ink-subtle py-8">
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
                <TableCell className="text-xs text-ink-subtle whitespace-nowrap font-mono">
                  {a.timestamp
                    ? new Date(a.timestamp).toLocaleTimeString('en-US', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })
                    : '—'}
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-[10px] font-medium">
                    {a.type.toUpperCase()}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-ink-muted">{a.message}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Card>
  )
}

async function AgentStatusCard() {
  const { agents } = await loadHealth()
  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Status</CardTitle>
      </CardHeader>
      {agents.length === 0 ? (
        <div className="text-center py-8 text-ink-subtle">
          <Activity className="size-8 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No agent activity yet</p>
          <p className="text-xs mt-1 text-ink-tertiary">
            Generate content to see real-time agent status
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {agents.map((a) => {
            const isUsingFallback = a.fallback_model !== null
            const latencyColor =
              a.last_latency_ms && a.last_latency_ms > 5000
                ? 'text-[var(--status-error)]'
                : a.last_latency_ms && a.last_latency_ms > 2000
                ? 'text-[var(--status-warning)]'
                : 'text-[var(--status-success)]'
            return (
              <li key={a.agent_name} className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-ink">{a.agent_name}</span>
                  <div className="flex items-center gap-2">
                    <span
                      className={
                        a.status === 'healthy'
                          ? 'status-success-soft text-[10px] font-medium px-1.5 py-0.5 rounded'
                          : 'status-warning-soft text-[10px] font-medium px-1.5 py-0.5 rounded'
                      }
                    >
                      {a.status === 'healthy'
                        ? 'Online'
                        : a.status === 'degraded'
                        ? 'Degraded'
                        : 'Offline'}
                    </span>
                    {isUsingFallback && (
                      <span className="status-error-soft text-[10px] font-medium px-1.5 py-0.5 rounded">
                        Fallback
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs text-ink-subtle pl-2">
                  <span>{a.current_model || 'Unknown'}</span>
                  <span className={`font-mono ${latencyColor}`}>
                    {a.last_latency_ms ? `${a.last_latency_ms}ms` : 'N/A'}
                  </span>
                </div>
                <div className="text-xs text-ink-tertiary pl-2">
                  Engine: <span className="font-medium text-ink-subtle">{a.engine || 'Unknown'}</span>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}

// ── Skeletons ──────────────────────────────────────────────────────

function KpiRowSkeleton({ count }: { count: number }) {
  return (
    <div
      className="grid gap-4"
      style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className="h-28 rounded-lg" />
      ))}
    </div>
  )
}

function PipelineSkeleton() {
  return <Skeleton className="h-32 rounded-lg" />
}

function TableSkeleton({ title }: { title: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-6 w-full" />
        ))}
      </div>
    </Card>
  )
}
