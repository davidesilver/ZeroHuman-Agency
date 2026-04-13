'use client'

import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { KPICard } from '@/components/dashboard/kpi-card'
import { cn } from '@/lib/utils'

const CONTENT_TYPES = ['Newsletter', 'Social', 'Blog', 'LinkedIn'] as const

interface Round {
  id: string
  round_number: number
  champion_text: string
  challenger_text: string
  hook_type_champion: string | null
  hook_type_challenger: string | null
  winner: string | null
}

interface Session {
  id: string
  topic: string
  content_type: string
  status: string
  rounds_completed: number | null
  max_rounds: number | null
  current_champion: string | null
  user_votes: Record<string, string> | null
}

export default function WritingLabPage() {
  const [contentType, setContentType] = useState<string>('Newsletter')
  const [session, setSession] = useState<Session | null>(null)
  const [currentRound, setCurrentRound] = useState<Round | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [topic, setTopic] = useState('')

  const startSession = useCallback(async () => {
    if (!topic.trim()) return
    setIsLoading(true)
    try {
      const resp = await fetch('/api/writing-lab/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, content_type: contentType.toLowerCase() }),
      })
      const json = await resp.json()
      if (json.success) {
        setSession(json.data.session)
        setCurrentRound(json.data.round)
      }
    } catch {}
    setIsLoading(false)
  }, [topic, contentType])

  const vote = useCallback(async (winner: string) => {
    if (!session || !currentRound) return
    setIsLoading(true)
    try {
      const resp = await fetch(`/api/writing-lab/sessions/${session.id}/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ winner }),
      })
      const json = await resp.json()
      if (json.success) {
        if (json.data.status === 'completed') {
          setSession(prev => prev ? { ...prev, status: 'completed', current_champion: json.data.champion } : null)
          setCurrentRound(null)
        } else {
          setCurrentRound(json.data.round)
          setSession(prev => prev ? { ...prev, rounds_completed: json.data.rounds_completed } : null)
        }
      }
    } catch {}
    setIsLoading(false)
  }, [session, currentRound])

  const roundsCompleted = session?.rounds_completed || 0
  const maxRounds = session?.max_rounds || 50
  const votes = session?.user_votes || {}
  const championWins = Object.values(votes).filter(v => v === 'champion').length
  const winRate = roundsCompleted > 0 ? Math.round((championWins / roundsCompleted) * 100) : 0

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
              disabled={!!session && session.status === 'active'}
            >
              {ct}
            </Button>
          ))}
        </div>
      </div>

      {/* Start session */}
      {!session && (
        <Card>
          <CardContent className="pt-4 flex gap-3 items-end">
            <div className="flex-1">
              <label className="text-sm font-medium mb-1 block">Topic</label>
              <input
                type="text"
                value={topic}
                onChange={e => setTopic(e.target.value)}
                placeholder="es. Come l'AI sta cambiando il marketing B2B"
                className="w-full px-3 py-2 rounded-md border border-border bg-background text-sm"
              />
            </div>
            <Button onClick={startSession} disabled={isLoading || !topic.trim()}>
              {isLoading ? 'Generando...' : 'Avvia Sessione'}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* A/B Panels */}
      <div className="grid grid-cols-2 gap-4">
        <Card className="relative">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between mb-3">
              <Badge variant="outline" className="text-[10px] font-medium">CAMPIONE ATTUALE</Badge>
              {currentRound && <Badge className="bg-staging-bg text-white text-[10px]">A</Badge>}
            </div>
            <div className="min-h-[200px] rounded-md bg-secondary/50 p-4 text-sm whitespace-pre-wrap">
              {currentRound?.champion_text || (session?.current_champion || 'Avvia una sessione per generare il testo campione.')}
            </div>
            {currentRound?.hook_type_champion && (
              <p className="text-xs text-muted-foreground mt-2">Hook: {currentRound.hook_type_champion}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between mb-3">
              <Badge variant="outline" className="text-[10px] font-medium">NUOVA VERSIONE</Badge>
              {currentRound && <Badge variant="outline" className="text-[10px]">B</Badge>}
            </div>
            <div className="min-h-[200px] rounded-md bg-secondary/50 p-4 text-sm whitespace-pre-wrap">
              {currentRound?.challenger_text || 'Il challenger verrà generato automaticamente ad ogni round.'}
            </div>
            {currentRound?.hook_type_challenger && (
              <p className="text-xs text-muted-foreground mt-2">Hook: {currentRound.hook_type_challenger}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Vote Buttons */}
      <div className="flex items-center justify-center gap-4">
        <Button
          variant="outline"
          size="lg"
          disabled={!currentRound || isLoading}
          onClick={() => vote('champion')}
        >
          Scegli A
        </Button>
        <Button
          variant="outline"
          size="lg"
          disabled={!currentRound || isLoading}
          onClick={() => vote('draw')}
        >
          Pari
        </Button>
        <Button
          variant="outline"
          size="lg"
          disabled={!currentRound || isLoading}
          onClick={() => vote('challenger')}
        >
          Scegli B
        </Button>
      </div>

      {session?.status === 'completed' && (
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-staging-bg font-medium">Sessione completata!</p>
            <p className="text-sm text-muted-foreground mt-1">
              Il campione finale è stato salvato dopo {roundsCompleted} round.
            </p>
            <Button className="mt-3" onClick={() => { setSession(null); setCurrentRound(null); setTopic('') }}>
              Nuova Sessione
            </Button>
          </CardContent>
        </Card>
      )}

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
        <KPICard title="Round" value={`${roundsCompleted}/${maxRounds}`} subtitle={session ? (session.status === 'active' ? 'In corso' : 'Completata') : 'Sessione non avviata'} />
        <KPICard title="Hook type" value={currentRound?.hook_type_challenger || '—'} subtitle="Hook corrente del challenger" />
        <KPICard title="Win rate campione" value={roundsCompleted > 0 ? `${winRate}%` : '—'} subtitle="% vittorie versione A" />
      </div>
    </div>
  )
}
