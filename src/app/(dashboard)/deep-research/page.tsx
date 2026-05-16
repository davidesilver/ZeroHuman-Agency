'use client'

import { useCallback, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { FeatureGate } from '@/components/ui/feature-gate'
import { ErrorCard } from '@/components/ui/error-card'
import { EmptyState } from '@/components/ui/empty-state'
import { usePolling } from '@/hooks/use-polling'
import { getStatusVariant } from '@/lib/status-colors'
import { useBrand } from '@/lib/brand-context'
import { Loader2, Search, ChevronDown, ChevronUp, ExternalLink, Sparkles, Microscope } from 'lucide-react'

interface Job {
  id: string
  topic: string
  depth: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  error?: string
  created_at: string
  completed_at?: string
}

function DeepResearchContent() {
  const { activeBrand } = useBrand()
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [topic, setTopic] = useState('')
  const [depth, setDepth] = useState(3)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, any>>({})
  const [generatingIdeas, setGeneratingIdeas] = useState<Record<string, boolean>>({})
  const [ideaResults, setIdeaResults] = useState<Record<string, { created: number; items: any[] }>>({})

  const loadJobs = useCallback(async () => {
    try {
      const res = await fetch('/api/research/deep')
      if (!res.ok) {
        setError(`Failed to load jobs (${res.status})`)
        return
      }
      setJobs(await res.json())
      setError(null)
    } catch {
      setError('Unable to reach the research service')
    } finally {
      setLoading(false)
    }
  }, [])

  usePolling(loadJobs, 10_000)

  async function submit() {
    if (!topic.trim()) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const res = await fetch('/api/research/deep', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topic.trim(), depth }),
      })
      if (!res.ok) {
        setSubmitError(`Failed to start research (${res.status})`)
        return
      }
      setTopic('')
      await loadJobs()
    } catch {
      setSubmitError('Network error — unable to start research')
    } finally {
      setSubmitting(false)
    }
  }

  async function loadResults(jobId: string) {
    if (results[jobId]) { setExpandedId(expandedId === jobId ? null : jobId); return }
    try {
      const res = await fetch(`/api/research/deep/${jobId}/results`)
      if (res.ok) {
        const data = await res.json()
        setResults(r => ({ ...r, [jobId]: data }))
      }
    } catch { /* silent — results panel simply won't expand */ }
    setExpandedId(jobId)
  }

  async function generateIdeas(jobId: string) {
    setGeneratingIdeas(g => ({ ...g, [jobId]: true }))
    try {
      const res = await fetch(`/api/research/deep/${jobId}/generate-ideas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ n: 5 }),
      })
      if (res.ok) {
        const data = await res.json()
        setIdeaResults(r => ({ ...r, [jobId]: data }))
      }
    } finally {
      setGeneratingIdeas(g => ({ ...g, [jobId]: false }))
    }
  }

  if (!activeBrand) {
    return (
      <div className="p-6 max-w-3xl">
        <EmptyState icon={Microscope} message="Select a brand to use Deep Research." />
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold">Deep Research</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Automated multi-source research using local-deep-research. Results feed into ideation.
        </p>
      </div>

      {/* Submit form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Search className="h-4 w-4" /> New Research Job
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Topic</Label>
            <Input
              placeholder="e.g. AI trends in B2B SaaS marketing 2025"
              value={topic}
              onChange={e => setTopic(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && submit()}
              className="mt-1"
            />
          </div>
          <div>
            <Label>Depth (1=fast, 5=deep)</Label>
            <div className="flex gap-2 mt-1">
              {[1, 2, 3, 4, 5].map(d => (
                <button
                  key={d}
                  onClick={() => setDepth(d)}
                  className={`h-8 w-8 rounded text-sm font-medium transition-colors ${
                    depth === d
                      ? 'bg-primary text-primary-foreground'
                      : 'border hover:bg-muted'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Deeper = more sources + longer runtime. Default cap is depth 3 per brand.
            </p>
          </div>
          {submitError && (
            <p className="text-xs text-destructive">{submitError}</p>
          )}
          <Button onClick={submit} disabled={submitting || !topic.trim()}>
            {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Start Research
          </Button>
        </CardContent>
      </Card>

      {/* Jobs list */}
      <div className="space-y-2">
        {error ? (
          <ErrorCard message={error} onRetry={loadJobs} />
        ) : loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading jobs...
          </div>
        ) : jobs.length === 0 ? (
          <EmptyState icon={Search} message="No research jobs yet." />
        ) : (
          jobs.map(job => (
            <Card key={job.id} className="overflow-hidden">
              <div className="flex items-center gap-3 p-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{job.topic}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Depth {job.depth} · {new Date(job.created_at).toLocaleString()}
                  </p>
                </div>
                <Badge variant={(getStatusVariant(job.status)) as any}>
                  {job.status}
                </Badge>
                {job.status === 'running' && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
                {job.status === 'completed' && (
                  <Button size="sm" variant="ghost" onClick={() => loadResults(job.id)}>
                    {expandedId === job.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                )}
              </div>
              {expandedId === job.id && results[job.id] && (
                <div className="border-t bg-muted/30 p-4 space-y-4">
                  <div className="prose prose-sm max-w-none">
                    <pre className="whitespace-pre-wrap text-xs leading-relaxed max-h-96 overflow-y-auto">
                      {typeof results[job.id].result === 'string'
                        ? results[job.id].result
                        : JSON.stringify(results[job.id].result, null, 2)}
                    </pre>
                  </div>
                  {results[job.id].sources?.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-muted-foreground">Sources ({results[job.id].sources.length})</p>
                      {results[job.id].sources.slice(0, 10).map((s: any, i: number) => (
                        <div key={i} className="flex items-center gap-1 text-xs text-muted-foreground">
                          <ExternalLink className="h-3 w-3 shrink-0" />
                          <a href={s.url ?? s} target="_blank" rel="noopener" className="hover:underline truncate">
                            {s.title ?? s.url ?? s}
                          </a>
                        </div>
                      ))}
                    </div>
                  )}
                  {/* Generate ideas handoff */}
                  <div className="pt-2 border-t">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => generateIdeas(job.id)}
                      disabled={generatingIdeas[job.id]}
                    >
                      {generatingIdeas[job.id]
                        ? <Loader2 className="h-3 w-3 animate-spin mr-1" />
                        : <Sparkles className="h-3 w-3 mr-1" />}
                      Generate content ideas
                    </Button>
                    {ideaResults[job.id] && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs text-muted-foreground">
                          {ideaResults[job.id].created} ideas added to Research pipeline
                        </p>
                        {ideaResults[job.id].items.map((item: any, i: number) => (
                          <div key={i} className="rounded border bg-background p-2">
                            <p className="text-xs font-medium">{item.title}</p>
                            {item.summary && (
                              <p className="text-xs text-muted-foreground mt-0.5">{item.summary}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  )
}

export default function DeepResearchPage() {
  const { activeBrand } = useBrand()
  return (
    <FeatureGate flag="deep_research_enabled" brandId={activeBrand?.id}>
      <DeepResearchContent />
    </FeatureGate>
  )
}
