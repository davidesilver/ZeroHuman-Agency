'use client'

import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { KPICard } from '@/components/dashboard/kpi-card'
import { cn } from '@/lib/utils'
import { Loader2, Sparkles } from 'lucide-react'

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

interface GodReview {
  advocate_feedback: string | null
  advocate_score: number | null
  factcheck_feedback: string | null
  factcheck_issues: unknown[] | null
  creative_feedback: string | null
  creative_suggestions: unknown[] | null
  synthesis_result: string | null
  final_verdict: string | null
}

export default function WritingLabPage() {
  const [contentType, setContentType] = useState<string>('Newsletter')
  const [session, setSession] = useState<Session | null>(null)
  const [currentRound, setCurrentRound] = useState<Round | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [topic, setTopic] = useState('')
  const [godReview, setGodReview] = useState<GodReview | null>(null)
  const [godLoading, setGodLoading] = useState(false)

  const startSession = useCallback(async () => {
    if (!topic.trim()) return
    setIsLoading(true)
    setGodReview(null)
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

  const runGodMode = useCallback(async () => {
    if (!session?.current_champion && !currentRound?.champion_text) return
    setGodLoading(true)
    setGodReview(null)
    try {
      const text = session?.current_champion || currentRound?.champion_text || ''
      const draftResp = await fetch('/api/content/drafts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: session?.topic || 'Writing Lab Champion',
          body: text,
          platform: contentType.toLowerCase(),
          content_type: 'post',
          status: 'draft',
        }),
      })
      const draftJson = await draftResp.json()
      if (!draftJson.success) return

      const draftId = draftJson.data?.id
      if (!draftId) return

      await fetch(`/api/content/drafts/${draftId}/god-mode`, { method: 'POST' })

      const reviewResp = await fetch(`/api/god-mode-reviews?draft_id=${draftId}`)
      const reviewJson = await reviewResp.json()
      if (reviewJson.success && reviewJson.data) {
        setGodReview(reviewJson.data)
      }
    } catch {}
    setGodLoading(false)
  }, [session, currentRound, contentType])

  // Fetch latest GOD review on mount
  useEffect(() => {
    fetch('/api/god-mode-reviews')
      .then(r => r.json())
      .then(json => {
        if (json.success && json.data) setGodReview(json.data)
      })
      .catch(() => {})
  }, [])

  const roundsCompleted = session?.rounds_completed || 0
  const maxRounds = session?.max_rounds || 50
  const votes = session?.user_votes || {}
  const championWins = Object.values(votes).filter(v => v === 'champion').length
  const winRate = roundsCompleted > 0 ? Math.round((championWins / roundsCompleted) * 100) : 0

  const godAgents = [
    {
      name: 'Advocate',
      color: 'bg-brand-primary',
      feedback: godReview?.advocate_feedback,
      score: godReview?.advocate_score,
    },
    {
      name: 'FactChecker',
      color: 'bg-staging-bg',
      feedback: godReview?.factcheck_feedback,
      extra: godReview?.factcheck_issues?.length
        ? `${godReview.factcheck_issues.length} issues found`
        : null,
    },
    {
      name: 'Creative',
      color: 'bg-purple-500',
      feedback: godReview?.creative_feedback,
      extra: godReview?.creative_suggestions?.length
        ? `${godReview.creative_suggestions.length} suggestions`
        : null,
    },
  ]

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
                placeholder="e.g. How AI is changing B2B marketing"
                className="w-full px-3 py-2 rounded-md border border-border bg-background text-sm"
              />
            </div>
            <Button onClick={startSession} disabled={isLoading || !topic.trim()}>
              {isLoading ? 'Generating...' : 'Start Session'}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* A/B Panels */}
      <div className="grid grid-cols-2 gap-4">
        <Card className="relative">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between mb-3">
              <Badge variant="outline" className="text-[10px] font-medium">CURRENT CHAMPION</Badge>
              {currentRound && <Badge className="bg-staging-bg text-white text-[10px]">A</Badge>}
            </div>
            <div className="min-h-[200px] rounded-md bg-secondary/50 p-4 text-sm whitespace-pre-wrap">
              {currentRound?.champion_text || (session?.current_champion || 'Start a session to generate champion text.')}
            </div>
            {currentRound?.hook_type_champion && (
              <p className="text-xs text-muted-foreground mt-2">Hook: {currentRound.hook_type_champion}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between mb-3">
              <Badge variant="outline" className="text-[10px] font-medium">NEW VERSION</Badge>
              {currentRound && <Badge variant="outline" className="text-[10px]">B</Badge>}
            </div>
            <div className="min-h-[200px] rounded-md bg-secondary/50 p-4 text-sm whitespace-pre-wrap">
              {currentRound?.challenger_text || 'The challenger will be generated automatically each round.'}
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
          Pick A
        </Button>
        <Button
          variant="outline"
          size="lg"
          disabled={!currentRound || isLoading}
          onClick={() => vote('draw')}
        >
          Draw
        </Button>
        <Button
          variant="outline"
          size="lg"
          disabled={!currentRound || isLoading}
          onClick={() => vote('challenger')}
        >
          Pick B
        </Button>
      </div>

      {session?.status === 'completed' && (
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-staging-bg font-medium">Session completed!</p>
            <p className="text-sm text-muted-foreground mt-1">
              The final champion was saved after {roundsCompleted} rounds.
            </p>
            <Button className="mt-3" onClick={() => { setSession(null); setCurrentRound(null); setTopic(''); setGodReview(null) }}>
              New Session
            </Button>
          </CardContent>
        </Card>
      )}

      {/* GOD Mode Feedback — connected to real data */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium">GOD Mode Feedback</h3>
            {(session?.current_champion || currentRound?.champion_text) && (
              <Button
                size="sm"
                variant="outline"
                onClick={runGodMode}
                disabled={godLoading}
                className="text-xs"
              >
                {godLoading ? (
                  <Loader2 className="size-3 animate-spin mr-1" />
                ) : (
                  <Sparkles className="size-3 mr-1" />
                )}
                {godLoading ? 'Running...' : 'Run GOD Mode'}
              </Button>
            )}
          </div>

          {godReview?.final_verdict && (
            <div className="mb-4 flex items-center gap-2">
              <Badge
                variant={godReview.final_verdict === 'pass' ? 'default' : 'outline'}
                className={cn(
                  'text-[10px]',
                  godReview.final_verdict === 'pass' && 'bg-green-600',
                  godReview.final_verdict === 'reject' && 'bg-red-600 text-white'
                )}
              >
                {godReview.final_verdict.toUpperCase()}
              </Badge>
              {godReview.synthesis_result && (
                <span className="text-xs text-muted-foreground">{godReview.synthesis_result}</span>
              )}
            </div>
          )}

          <div className="grid grid-cols-3 gap-4">
            {godAgents.map(agent => (
              <div key={agent.name} className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className={cn('size-2 rounded-full', agent.color)} />
                  <span className="text-xs font-medium">{agent.name}</span>
                  {'score' in agent && agent.score != null && (
                    <span className="text-[10px] text-muted-foreground">({agent.score}/10)</span>
                  )}
                </div>
                <div className="rounded-md bg-secondary/50 p-3 text-xs text-muted-foreground min-h-[60px]">
                  {agent.feedback || (godLoading ? 'Running analysis...' : 'Run GOD Mode to get feedback.')}
                </div>
                {'extra' in agent && agent.extra && (
                  <p className="text-[10px] text-muted-foreground">{agent.extra}</p>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Session Stats */}
      <div className="grid grid-cols-3 gap-4">
        <KPICard title="Round" value={`${roundsCompleted}/${maxRounds}`} subtitle={session ? (session.status === 'active' ? 'In progress' : 'Completed') : 'Session not started'} />
        <KPICard title="Hook type" value={currentRound?.hook_type_challenger || '—'} subtitle="Current challenger hook" />
        <KPICard title="Champion win rate" value={roundsCompleted > 0 ? `${winRate}%` : '—'} subtitle="% wins version A" />
      </div>
    </div>
  )
}
