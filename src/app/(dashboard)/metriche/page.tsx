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

const HOURS = ['6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21']
const WEEKDAYS = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']

export default function MetrichePage() {
  const [activeTab, setActiveTab] = useState('newsletter')

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Metriche</h1>

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

      <div className="grid grid-cols-3 gap-4">
        <KPICard title="Open rate medio" value="—" subtitle="Collegare ESP per dati reali" />
        <KPICard title="Iscritti totali" value="—" subtitle="Collegare ESP" />
        <KPICard title="CTR medio" value="—" subtitle="Collegare ESP" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <Card className="lg:col-span-3">
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Open Rate Trend (30 giorni)</h3>
            <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
              Grafico disponibile con dati reali
            </div>
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardContent className="pt-4">
            <h3 className="text-sm font-medium mb-4">Crescita Iscritti</h3>
            <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
              Grafico disponibile con dati reali
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-4">Finestra Ottimale di Invio</h3>
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
          <p className="text-xs text-muted-foreground mt-2">Heatmap si popola con dati engagement reali</p>
        </CardContent>
      </Card>
    </div>
  )
}
