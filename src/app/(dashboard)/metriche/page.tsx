'use client'

import { useState } from 'react'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

const TABS = [
  { key: 'newsletter', label: 'NEWSLETTER' },
  { key: 'social', label: 'SOCIAL' },
  { key: 'web', label: 'WEB' },
  { key: 'revenue', label: 'REVENUE' },
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
            <h3 className="text-sm font-medium mb-4">Open Rate Trend (30 days)</h3>
            <ComingSoon label="Chart available with real data" />
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Subscriber Growth</h3>
            <ComingSoon label="Chart available with real data" />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-4">Optimal Send Window</h3>
          <div className="overflow-x-auto">
            <div className="grid gap-px" style={{ gridTemplateColumns: `60px repeat(${WEEKDAYS.length}, 1fr)` }}>
              <div />
              {WEEKDAYS.map(d => (
                <div key={d} className="text-center text-xs text-muted-foreground py-1">{d}</div>
              ))}
              {HOURS.map(h => (
                <div key={h} className="contents">
                  <div className="text-xs text-muted-foreground text-right pr-2 py-1">{h}:00</div>
                  {WEEKDAYS.map(d => (
                    <div key={`${h}-${d}`} className="bg-secondary rounded-sm h-6" />
                  ))}
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Impressions by platform (30d)</h3>
            <ComingSoon label="Connect LinkedIn / Twitter / Instagram to see data" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Top posts by engagement</h3>
            <ComingSoon label="Connect social accounts to see top posts" />
          </CardContent>
        </Card>
      </div>
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

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <Card className="lg:col-span-3">
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Traffic trend (30 days)</h3>
            <ComingSoon label="Connect Google Analytics or Plausible" />
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Top pages</h3>
            <ComingSoon label="Connect analytics to see top pages" />
          </CardContent>
        </Card>
      </div>
    </>
  )
}

function RevenueTab() {
  return (
    <>
      <div className="grid grid-cols-3 gap-4">
        <KPICard title="MRR" value="—" subtitle="Track in Revenue page" />
        <KPICard title="Affiliate revenue MTD" value="—" subtitle="Configure in Revenue page" />
        <KPICard title="Sponsorship revenue MTD" value="—" subtitle="Configure in Revenue page" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Revenue trend (6 months)</h3>
            <ComingSoon label="Add deals in the Revenue page to see trend" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Revenue by channel</h3>
            <ComingSoon label="Add deals in the Revenue page to see breakdown" />
          </CardContent>
        </Card>
      </div>
    </>
  )
}

export default function MetrichePage() {
  const [activeTab, setActiveTab] = useState<Tab>('newsletter')

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

      {activeTab === 'newsletter' && <NewsletterTab />}
      {activeTab === 'social' && <SocialTab />}
      {activeTab === 'web' && <WebTab />}
      {activeTab === 'revenue' && <RevenueTab />}
    </div>
  )
}
