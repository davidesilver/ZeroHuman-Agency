'use client'

import { useCallback, useEffect, useState } from 'react'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const TABS = [
  { key: 'pipeline', label: 'PIPELINE' },
  { key: 'newsletter', label: 'NEWSLETTER' },
  { key: 'social', label: 'SOCIAL' },
  { key: 'web', label: 'WEB' },
] as const

type Tab = (typeof TABS)[number]['key']

const HOURS = ['6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21']
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function ComingSoon({ label }: { label: string }) {
  return (
    <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
      {label}
    </div>
  )
}

// ── Pipeline tab — real data from Supabase ───────────────────────────────────
interface PipelineData {
  research: { total: number; approved: number; scored: number; new: number }
  drafts: { total: number; draft: number; in_review: number; approved: number; published: number; scheduled: number }
  newsletters: { total: number; sent: number; draft: number }
  memory: { total: number; by_kind: { kind: string; count: number }[] }
  costs: { spend_today: number; daily_budget: number | null }
}

function PipelineTab() {
  const [data, setData] = useState<PipelineData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [researchResp, draftsResp, newslettersResp, memoryResp, costsResp] = await Promise.all([
        fetch('/api/research/items?per_page=1').then(r => r.json()),
        fetch('/api/content/drafts?per_page=1').then(r => r.json()),
        fetch('/api/newsletter?per_page=1').then(r => r.json()),
        fetch('/api/memory/facts?limit=1').then(r => r.json()),
        fetch('/api/system/costs?period=today').then(r => r.json()),
      ])

      // Parallel counts by status for research_items
      const [approvedR, scoredR, newR] = await Promise.all([
        fetch('/api/research/items?per_page=1&status=approved').then(r => r.json()),
        fetch('/api/research/items?per_page=1&status=scored').then(r => r.json()),
        fetch('/api/research/items?per_page=1&status=new').then(r => r.json()),
      ])

      // Parallel draft counts by status
      const [draftD, reviewD, approvedD, publishedD, scheduledD] = await Promise.all([
        fetch('/api/content/drafts?per_page=1&status=draft').then(r => r.json()),
        fetch('/api/content/drafts?per_page=1&status=in_review').then(r => r.json()),
        fetch('/api/content/drafts?per_page=1&status=approved').then(r => r.json()),
        fetch('/api/content/drafts?per_page=1&status=published').then(r => r.json()),
        fetch('/api/content/drafts?per_page=1&status=scheduled').then(r => r.json()),
      ])

      // safe() extracts total from paginated responses (meta.total) or newsletter arrays
      const safeCount = (j: { success?: boolean; data?: { meta?: { total?: number }; newsletters?: unknown[]; drafts?: unknown[] } }) => {
        if (!j?.success) return 0
        return j.data?.meta?.total ?? j.data?.newsletters?.length ?? j.data?.drafts?.length ?? 0
      }
      // memory/facts returns data as a direct array
      const memTotal = memoryResp?.success ? (Array.isArray(memoryResp.data) ? memoryResp.data.length : 0) : 0

      setData({
        research: {
          total: safeCount(researchResp),
          approved: safeCount(approvedR),
          scored: safeCount(scoredR),
          new: safeCount(newR),
        },
        drafts: {
          total: safeCount(draftsResp),
          draft: safeCount(draftD),
          in_review: safeCount(reviewD),
          approved: safeCount(approvedD),
          published: safeCount(publishedD),
          scheduled: safeCount(scheduledD),
        },
        newsletters: {
          total: safeCount(newslettersResp),
          sent: (newslettersResp.data?.newsletters || []).filter((n: { status: string }) => n.status === 'sent').length,
          draft: (newslettersResp.data?.newsletters || []).filter((n: { status: string }) => n.status === 'draft').length,
        },
        memory: {
          total: memTotal,
          by_kind: memoryResp.data?.by_kind || [],
        },
        costs: {
          spend_today: costsResp.data?.spend_today ?? 0,
          daily_budget: costsResp.data?.brand_budget ?? costsResp.data?.daily_budget ?? null,
        },
      })
    } catch {
      // leave null — show loading state
    }
    setLoading(false)
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  if (loading) return <div className="text-center py-12 text-muted-foreground">Loading pipeline data…</div>
  if (!data) return <div className="text-center py-12 text-destructive text-sm">Failed to load — is the Python backend running?</div>

  const budgetPct = data.costs.daily_budget != null && data.costs.daily_budget > 0
    ? Math.min((data.costs.spend_today / data.costs.daily_budget) * 100, 100)
    : 0

  return (
    <>
      {/* Research */}
      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-3">Research Pipeline</h3>
          <div className="grid grid-cols-4 gap-4">
            <KPICard title="Total items" value={data.research.total} />
            <KPICard title="New (unscored)" value={data.research.new} />
            <KPICard title="Scored" value={data.research.scored} />
            <KPICard title="Approved" value={data.research.approved} />
          </div>
        </CardContent>
      </Card>

      {/* Drafts */}
      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-3">Content Drafts</h3>
          <div className="grid grid-cols-5 gap-3">
            {[
              { label: 'Draft', value: data.drafts.draft, color: 'bg-muted' },
              { label: 'In Review', value: data.drafts.in_review, color: 'bg-amber-100 dark:bg-amber-900/30' },
              { label: 'Approved', value: data.drafts.approved, color: 'bg-green-100 dark:bg-green-900/30' },
              { label: 'Scheduled', value: data.drafts.scheduled, color: 'bg-blue-100 dark:bg-blue-900/30' },
              { label: 'Published', value: data.drafts.published, color: 'bg-emerald-100 dark:bg-emerald-900/30' },
            ].map(s => (
              <div key={s.label} className={cn('rounded-lg p-3 text-center', s.color)}>
                <div className="text-2xl font-bold">{s.value}</div>
                <div className="text-xs text-muted-foreground mt-1">{s.label}</div>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-2">Total: {data.drafts.total} drafts across all platforms</p>
        </CardContent>
      </Card>

      {/* Newsletters */}
      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-3">Newsletters</h3>
          <div className="grid grid-cols-3 gap-4">
            <KPICard title="Total editions" value={data.newsletters.total} />
            <KPICard title="Sent" value={data.newsletters.sent} />
            <KPICard title="Drafts pending" value={data.newsletters.draft} />
          </div>
        </CardContent>
      </Card>

      {/* Costs today */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium">API Spend Today</h3>
            <span className="text-sm text-muted-foreground">
              {data.costs.daily_budget != null
                ? `$${data.costs.spend_today.toFixed(4)} / $${data.costs.daily_budget.toFixed(2)}`
                : `$${data.costs.spend_today.toFixed(4)} (unlimited)`}
            </span>
          </div>
          <div className="w-full bg-secondary rounded-full h-2.5">
            <div
              className={cn('h-2.5 rounded-full transition-all', budgetPct > 80 ? 'bg-destructive' : 'bg-green-500')}
              style={{ width: `${budgetPct}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {data.costs.daily_budget == null
              ? 'Unlimited spend'
              : budgetPct < 1
                ? 'No spend today'
                : `${budgetPct.toFixed(1)}% of daily budget`}
          </p>
        </CardContent>
      </Card>
    </>
  )
}

// ── Newsletter/Social/Web stubs ──────────────────────────────────────────────
function NewsletterTab() {
  return (
    <>
      <div className="grid grid-cols-3 gap-4">
        <KPICard title="Avg open rate" value="—" subtitle="Connect ESP for real data" />
        <KPICard title="Total subscribers" value="—" subtitle="Connect ESP" />
        <KPICard title="Avg CTR" value="—" subtitle="Connect ESP" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <Card className="lg:col-span-3">
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-2">Open Rate Trend (30 days)</h3>
            <ComingSoon label="Chart available with real ESP data" />
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-2">Subscriber Growth</h3>
            <ComingSoon label="Chart available with real ESP data" />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-2">Optimal Send Window</h3>
          <div className="overflow-x-auto">
            <div className="grid gap-px" style={{ gridTemplateColumns: `60px repeat(${WEEKDAYS.length}, 1fr)` }}>
              <div />
              {WEEKDAYS.map(d => <div key={d} className="text-center text-xs text-muted-foreground py-1">{d}</div>)}
              {HOURS.map(h => (
                <div key={h} className="contents">
                  <div className="text-xs text-muted-foreground text-right pr-2 py-1">{h}:00</div>
                  {WEEKDAYS.map(d => <div key={`${h}-${d}`} className="bg-secondary rounded-sm h-6" />)}
                </div>
              ))}
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-2">Heatmap populates with real engagement data</p>
        </CardContent>
      </Card>
    </>
  )
}

function SocialTab() {
  return (
    <>
      <div className="grid grid-cols-3 gap-4">
        <KPICard title="Total impressions" value="—" subtitle="Connect social accounts" />
        <KPICard title="Avg engagement rate" value="—" subtitle="Connect social accounts" />
        <KPICard title="Followers growth" value="—" subtitle="Connect social accounts" />
      </div>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-2 mb-3">
            <h3 className="text-sm font-medium">Platform status</h3>
          </div>
          {['LinkedIn', 'Twitter/X', 'Instagram', 'TikTok'].map(p => (
            <div key={p} className="flex items-center justify-between py-2 border-b border-border last:border-0">
              <span className="text-sm">{p}</span>
              <Badge variant="outline" className="text-[10px] text-muted-foreground">Not connected</Badge>
            </div>
          ))}
          <p className="text-xs text-muted-foreground mt-3">
            Configure API tokens in Settings to enable social analytics.
          </p>
        </CardContent>
      </Card>
    </>
  )
}

function WebTab() {
  return (
    <>
      <div className="grid grid-cols-3 gap-4">
        <KPICard title="Monthly sessions" value="—" subtitle="Connect analytics" />
        <KPICard title="Avg time on page" value="—" subtitle="Connect analytics" />
        <KPICard title="Bounce rate" value="—" subtitle="Connect analytics" />
      </div>
      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-2">Traffic trend (30 days)</h3>
          <ComingSoon label="Connect Google Analytics or Plausible to enable" />
        </CardContent>
      </Card>
    </>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function MetrichePage() {
  const [activeTab, setActiveTab] = useState<Tab>('pipeline')

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Metrics</h1>

      <div className="flex gap-1 border-b border-border">
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab.key
                ? 'border-brand-primary text-brand-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'pipeline' && <PipelineTab />}
      {activeTab === 'newsletter' && <NewsletterTab />}
      {activeTab === 'social' && <SocialTab />}
      {activeTab === 'web' && <WebTab />}
    </div>
  )
}
