'use client'

import { useCallback, useEffect, useState } from 'react'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface Deal {
  id: string
  partner_name: string
  deal_type: string
  amount: number
  currency: string
  recurrence: string
  start_date: string
  end_date: string | null
  status: string
}

interface AgentHealth {
  agent_name: string
  uptime_pct: number | null
  status: string
  errors_today: number | null
  queue_size: number | null
}

export default function RevenuePage() {
  const [deals, setDeals] = useState<Deal[]>([])
  const [health, setHealth] = useState<{ agents: AgentHealth[]; summary: { avg_uptime: number; total_errors: number; total_queue: number } }>({
    agents: [],
    summary: { avg_uptime: 0, total_errors: 0, total_queue: 0 },
  })
  const [costs, setCosts] = useState({ spend_month: 0 })

  const fetchData = useCallback(async () => {
    const [healthRes, costsRes] = await Promise.all([
      fetch('/api/system/health').then(r => r.json()).catch(() => null),
      fetch('/api/system/costs?period=month').then(r => r.json()).catch(() => null),
    ])
    if (healthRes?.success) setHealth(healthRes.data)
    if (costsRes?.success) setCosts({ spend_month: costsRes.data.spend_month || 0 })
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Revenue & Pipeline Health</h1>

      <div className="grid grid-cols-4 gap-4">
        <KPICard title="MRR" value="—" subtitle="To configure" />
        <KPICard title="Affiliates MTD" value="—" subtitle="To configure" />
        <KPICard title="Sponsorship" value="—" subtitle="To configure" />
        <KPICard title="API Costs MTD" value={`$${costs.spend_month.toFixed(2)}`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Revenue 6 months</h3>
            <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
              Chart available with real data
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Pipeline Health</h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span>Agent Uptime</span>
                <span className="font-medium text-staging-bg">
                  {health.summary.avg_uptime > 0 ? `${health.summary.avg_uptime}%` : '—'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Errors today</span>
                <span className="font-medium">{health.summary.total_errors}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Queue size</span>
                <span className="font-medium">{health.summary.total_queue} items</span>
              </div>
              <div className="border-t border-border pt-3 space-y-2">
                {health.agents.length > 0 ? (
                  health.agents.map(a => (
                    <div key={a.agent_name} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">{a.agent_name}</span>
                        <span>{a.uptime_pct != null ? `${a.uptime_pct}%` : '—'}</span>
                      </div>
                      <Progress value={a.uptime_pct || 0} className="h-1.5" />
                    </div>
                  ))
                ) : (
                  ['ResearchBot', 'ScoringAgent', 'WriterAgent', 'EditorAgent', 'FactChecker'].map(name => (
                    <div key={name} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">{name}</span>
                        <span>—</span>
                      </div>
                      <Progress value={0} className="h-1.5" />
                    </div>
                  ))
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-4">Active Deals</h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Partner</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Expiry</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {deals.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                    No active deals. This section populates from the deals table.
                  </TableCell>
                </TableRow>
              ) : (
                deals.map(deal => (
                  <TableRow key={deal.id}>
                    <TableCell className="font-medium">{deal.partner_name}</TableCell>
                    <TableCell>{deal.deal_type}</TableCell>
                    <TableCell className="text-right">
                      {deal.currency === 'EUR' ? '€' : '$'}{Number(deal.amount).toFixed(2)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {deal.end_date ? new Date(deal.end_date).toLocaleDateString('en-US') : 'Ongoing'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={deal.status === 'active' ? 'default' : 'outline'} className="text-[10px]">
                        {deal.status.toUpperCase()}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
