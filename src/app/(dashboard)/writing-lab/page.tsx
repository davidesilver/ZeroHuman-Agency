'use client'

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { KPICard } from '@/components/dashboard/kpi-card'
import { cn } from '@/lib/utils'

const CONTENT_TYPES = ['Newsletter', 'Social', 'Blog', 'LinkedIn'] as const

export default function WritingLabPage() {
  const [contentType, setContentType] = useState<string>('Newsletter')

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Writing Lab</h1>
        <div className="flex gap-2">
          {CONTENT_TYPES.map(ct => (
            <Button
              key={ct}
              variant={contentType === ct ? 'default' : 'outline'}
              size="sm"
              onClick={() => setContentType(ct)}
            >
              {ct}
            </Button>
          ))}
        </div>
      </div>

      {/* Toolbar */}
      <Card>
        <CardContent className="pt-3 pb-3 flex items-center gap-2">
          <Button variant="outline" size="sm" className="font-bold">B</Button>
          <Button variant="outline" size="sm" className="italic">I</Button>
          <div className="w-px h-6 bg-border" />
          <Button variant="outline" size="sm">Genera AI</Button>
          <Button variant="outline" size="sm">Riscrivi</Button>
          <Button variant="outline" size="sm">Accorcia</Button>
        </CardContent>
      </Card>

      {/* A/B Panels */}
      <div className="grid grid-cols-2 gap-4">
        <Card className="relative">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between mb-3">
              <Badge variant="outline" className="text-[10px] font-medium">CAMPIONE ATTUALE</Badge>
              <Badge className="bg-staging-bg text-white text-[10px]">VINCITORE PREVISTO</Badge>
            </div>
            <div className="min-h-[200px] rounded-md bg-secondary/50 p-4 text-sm text-muted-foreground">
              Seleziona un topic e avvia una sessione A/B per generare il testo campione.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between mb-3">
              <Badge variant="outline" className="text-[10px] font-medium">NUOVA VERSIONE</Badge>
            </div>
            <div className="min-h-[200px] rounded-md bg-secondary/50 p-4 text-sm text-muted-foreground">
              Il challenger verrà generato automaticamente ad ogni round.
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Vote Buttons */}
      <div className="flex items-center justify-center gap-4">
        <Button variant="outline" size="lg" disabled>Scegli A</Button>
        <Button variant="outline" size="lg" disabled>Pari</Button>
        <Button variant="outline" size="lg" disabled>Scegli B</Button>
      </div>

      {/* GOD Mode Feedback */}
      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-medium mb-4">GOD Mode Feedback</h3>
          <div className="grid grid-cols-3 gap-4">
            {(['FactChecker', 'Advocate', 'Synthesizer'] as const).map(agent => (
              <div key={agent} className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className={cn(
                    'size-2 rounded-full',
                    agent === 'FactChecker' ? 'bg-staging-bg' :
                    agent === 'Advocate' ? 'bg-brand-primary' : 'bg-purple-500'
                  )} />
                  <span className="text-xs font-medium">{agent}</span>
                </div>
                <div className="rounded-md bg-secondary/50 p-3 text-xs text-muted-foreground min-h-[60px]">
                  Feedback disponibile dopo il primo round.
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Session Stats */}
      <div className="grid grid-cols-3 gap-4">
        <KPICard title="Round" value="0/50" subtitle="Sessione non avviata" />
        <KPICard title="Hook type" value="—" subtitle="Si popola con i round" />
        <KPICard title="Win rate campione" value="—" subtitle="% vittorie versione A" />
      </div>
    </div>
  )
}
