'use client'

import { KPICard } from '@/components/dashboard/kpi-card'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const AGENTS_HEALTH = [
  { name: 'ResearchBot', uptime: 98 },
  { name: 'ScoringAgent', uptime: 100 },
  { name: 'WriterAgent', uptime: 95 },
  { name: 'EditorAgent', uptime: 97 },
  { name: 'FactChecker', uptime: 100 },
]

export default function RevenuePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Revenue & Pipeline Health</h1>

      <div className="grid grid-cols-4 gap-4">
        <KPICard title="MRR" value="—" subtitle="Da configurare" />
        <KPICard title="Affiliati MTD" value="—" subtitle="Da configurare" />
        <KPICard title="Sponsorship" value="—" subtitle="Da configurare" />
        <KPICard title="Totale MTD" value="—" subtitle="Da configurare" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Revenue 6 mesi</h3>
            <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
              Grafico disponibile con dati reali
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Pipeline Health</h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span>Uptime Agenti</span>
                <span className="font-medium text-staging-bg">98.7%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>API Latency</span>
                <span className="font-medium">—</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Errori oggi</span>
                <span className="font-medium">0</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Queue size</span>
                <span className="font-medium">0 items</span>
              </div>
              <div className="border-t border-border pt-3 space-y-2">
                {AGENTS_HEALTH.map(a => (
                  <div key={a.name} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">{a.name}</span>
                      <span>{a.uptime}%</span>
                    </div>
                    <Progress value={a.uptime} className="h-1.5" />
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-4">Deal Attivi</h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Partner</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead className="text-right">Importo</TableHead>
                <TableHead>Scadenza</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  Nessun deal attivo. La sezione si popola dalla tabella deals.
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
