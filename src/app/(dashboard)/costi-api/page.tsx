'use client'

import { useCallback, useEffect, useState } from 'react'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Card, CardContent } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Progress } from '@/components/ui/progress'

interface AgentCost {
  agent_name: string
  model: string
  calls: number
  tokens_input: number
  tokens_output: number
  cost_usd: number
}

export default function CostiAPIPage() {
  const [data, setData] = useState<{
    spend_today: number
    spend_week: number
    spend_month: number
    daily_budget: number
    by_agent: AgentCost[]
  }>({ spend_today: 0, spend_week: 0, spend_month: 0, daily_budget: 15, by_agent: [] })

  const fetchCosts = useCallback(async () => {
    try {
      const resp = await fetch('/api/system/costs?period=today')
      const json = await resp.json()
      if (json.success) setData(json.data)
    } catch {}
  }, [])

  useEffect(() => { fetchCosts() }, [fetchCosts])

  const pct = Math.min((data.spend_today / data.daily_budget) * 100, 100)

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">API Costs</h1>

      <div className="grid grid-cols-3 gap-4">
        <KPICard title="Spend today" value={`$${data.spend_today.toFixed(2)}`} />
        <KPICard title="Spend this week" value={`$${data.spend_week.toFixed(2)}`} />
        <KPICard title="Spend this month" value={`$${data.spend_month.toFixed(2)}`} />
      </div>

      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Daily budget</span>
            <span className="text-sm text-muted-foreground">
              ${data.spend_today.toFixed(2)} / ${data.daily_budget.toFixed(2)}
            </span>
          </div>
          <Progress value={pct} className="h-3" />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-4">Costs over last 30 days by agent</h3>
          <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
            Chart available with real data from api_costs table
          </div>
        </CardContent>
      </Card>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Agent</TableHead>
            <TableHead>Model</TableHead>
            <TableHead className="text-right">Calls today</TableHead>
            <TableHead className="text-right">Token In</TableHead>
            <TableHead className="text-right">Token Out</TableHead>
            <TableHead className="text-right">Cost</TableHead>
            <TableHead className="text-right">% of Budget</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.by_agent.length === 0 ? (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                No costs recorded today.
              </TableCell>
            </TableRow>
          ) : (
            data.by_agent.map(agent => (
              <TableRow key={agent.agent_name}>
                <TableCell className="font-medium">{agent.agent_name}</TableCell>
                <TableCell className="text-muted-foreground">{agent.model}</TableCell>
                <TableCell className="text-right">{agent.calls}</TableCell>
                <TableCell className="text-right">{agent.tokens_input.toLocaleString()}</TableCell>
                <TableCell className="text-right">{agent.tokens_output.toLocaleString()}</TableCell>
                <TableCell className="text-right">${agent.cost_usd.toFixed(4)}</TableCell>
                <TableCell className="text-right">
                  {data.daily_budget > 0 ? `${((agent.cost_usd / data.daily_budget) * 100).toFixed(1)}%` : '0%'}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
