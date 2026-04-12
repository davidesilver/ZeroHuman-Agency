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

const AGENTS = [
  { name: 'research_orchestrator', model: 'Sonnet', label: 'Research' },
  { name: 'scoring_agent', model: 'Sonnet', label: 'Scoring' },
  { name: 'opus_writer', model: 'Opus', label: 'Writer' },
  { name: 'opus_editor', model: 'Opus', label: 'Editor' },
  { name: 'god_advocate', model: 'Sonnet', label: 'GOD Advocate' },
  { name: 'god_factcheck', model: 'Sonnet', label: 'GOD Factcheck' },
  { name: 'god_creative', model: 'Sonnet', label: 'GOD Creative' },
  { name: 'god_synthesis', model: 'Opus', label: 'GOD Synthesis' },
  { name: 'sonnet_adapter', model: 'Sonnet', label: 'Adapter' },
]

export default function CostiAPIPage() {
  const dailyBudget = 15.0
  const spentToday = 0

  const pct = Math.min((spentToday / dailyBudget) * 100, 100)
  const barColor = pct < 80 ? 'bg-staging-bg' : pct < 100 ? 'bg-brand-accent' : 'bg-red-500'

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Costi API</h1>

      <div className="grid grid-cols-3 gap-4">
        <KPICard title="Spesa oggi" value={`$${spentToday.toFixed(2)}`} />
        <KPICard title="Spesa settimana" value="$0.00" />
        <KPICard title="Spesa mese" value="$0.00" />
      </div>

      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Budget giornaliero</span>
            <span className="text-sm text-muted-foreground">${spentToday.toFixed(2)} / ${dailyBudget.toFixed(2)}</span>
          </div>
          <Progress value={pct} className="h-3" />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-4">Costi ultimi 30 giorni per agente</h3>
          <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
            Grafico disponibile con dati reali dalla tabella api_costs
          </div>
        </CardContent>
      </Card>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Agente</TableHead>
            <TableHead>Modello</TableHead>
            <TableHead className="text-right">Chiamate oggi</TableHead>
            <TableHead className="text-right">Token In</TableHead>
            <TableHead className="text-right">Token Out</TableHead>
            <TableHead className="text-right">Costo</TableHead>
            <TableHead className="text-right">% Budget</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {AGENTS.map(agent => (
            <TableRow key={agent.name}>
              <TableCell className="font-medium">{agent.label}</TableCell>
              <TableCell className="text-muted-foreground">{agent.model}</TableCell>
              <TableCell className="text-right">0</TableCell>
              <TableCell className="text-right">0</TableCell>
              <TableCell className="text-right">0</TableCell>
              <TableCell className="text-right">$0.00</TableCell>
              <TableCell className="text-right">0%</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
