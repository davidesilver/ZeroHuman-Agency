'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { CheckCircle2, Circle, X, ChevronRight, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const DISMISS_KEY = 'getting_started_dismissed'

interface SetupStatus {
  llm: boolean
  brand: boolean
  voice: boolean
  research: boolean
  draft: boolean
}

async function fetchStatus(): Promise<SetupStatus> {
  const [configResp, brandsResp, factsResp, researchResp, draftsResp] = await Promise.allSettled([
    fetch('/api/system/config').then(r => r.json()),
    fetch('/api/brands').then(r => r.json()),
    fetch('/api/memory/facts?limit=1').then(r => r.json()),
    fetch('/api/research?limit=1&status=approved').then(r => r.json()),
    fetch('/api/content?limit=1').then(r => r.json()),
  ])

  const config = configResp.status === 'fulfilled' ? configResp.value?.data : null
  const brands = brandsResp.status === 'fulfilled' ? brandsResp.value?.data : null
  const facts  = factsResp.status === 'fulfilled'  ? factsResp.value?.data  : null
  const research = researchResp.status === 'fulfilled' ? researchResp.value?.data : null
  const drafts = draftsResp.status === 'fulfilled'  ? draftsResp.value?.data  : null

  return {
    llm:      !!(config?.api_keys?.anthropic || config?.api_keys?.openrouter),
    brand:    Array.isArray(brands) && brands.length > 0,
    voice:    Array.isArray(facts) && facts.length > 0,
    research: Array.isArray(research) && research.length > 0,
    draft:    Array.isArray(drafts) && drafts.length > 0,
  }
}

export function GettingStartedBanner() {
  const [dismissed, setDismissed] = useState(true) // hidden until hydrated
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState<SetupStatus | null>(null)

  useEffect(() => {
    if (typeof window !== 'undefined' && localStorage.getItem(DISMISS_KEY) === 'true') {
      setDismissed(true)
      return
    }
    setDismissed(false)
    fetchStatus()
      .then(s => {
        setStatus(s)
        // Auto-dismiss if everything is complete
        if (s.llm && s.brand && s.voice && s.research && s.draft) {
          setDismissed(true)
        }
      })
      .catch(() => setStatus(null))
      .finally(() => setLoading(false))
  }, [])

  function dismiss() {
    if (typeof window !== 'undefined') localStorage.setItem(DISMISS_KEY, 'true')
    setDismissed(true)
  }

  if (dismissed) return null

  const completedCount = status
    ? [status.llm, status.brand, status.voice, status.research, status.draft].filter(Boolean).length
    : 0
  const totalCount = 5

  const items = [
    {
      label: 'Configure LLM provider',
      done: status?.llm ?? false,
      href: '/settings',
      detail: 'Add ANTHROPIC_API_KEY or OPENROUTER_API_KEY to .env.local',
    },
    {
      label: 'Create your first brand',
      done: status?.brand ?? false,
      href: '/brands',
      detail: 'Scopes all research, content, and settings',
    },
    {
      label: 'Set up brand voice',
      done: status?.voice ?? false,
      href: '/settings/brand-context',
      detail: 'Tone rules, principles, and examples for content generation',
    },
    {
      label: 'Run first research',
      done: status?.research ?? false,
      href: '/ricerca',
      detail: 'Discover and score content ideas from the web',
    },
    {
      label: 'Generate your first draft',
      done: status?.draft ?? false,
      href: '/writing-lab',
      detail: 'Create brand-aligned content from approved research items',
    },
  ]

  return (
    <Card className="mb-6 border-primary/20 bg-primary/5">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="text-base">Getting Started</CardTitle>
            {loading ? (
              <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
            ) : (
              <span className="text-xs text-muted-foreground">
                {completedCount} / {totalCount} complete
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/setup"
              className="inline-flex items-center gap-1 text-xs h-7 px-2 rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              Open Setup Wizard <ChevronRight className="size-3" />
            </Link>
            <button
              onClick={dismiss}
              className="text-muted-foreground hover:text-foreground transition-colors"
              title="Dismiss"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>

        {/* Progress bar */}
        {!loading && (
          <div className="mt-2 h-1.5 rounded-full bg-border overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${(completedCount / totalCount) * 100}%` }}
            />
          </div>
        )}
      </CardHeader>

      <CardContent className="pb-4">
        {loading ? (
          <div className="grid grid-cols-2 gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-5 rounded bg-muted animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {items.map(({ label, done, href, detail }) => (
              <Link
                key={label}
                href={done ? '#' : href}
                className={`flex items-start gap-2 rounded-md p-2 text-sm transition-colors
                  ${done ? 'opacity-60 cursor-default' : 'hover:bg-primary/10 cursor-pointer'}`}
                onClick={done ? (e => e.preventDefault()) : undefined}
              >
                {done ? (
                  <CheckCircle2 className="size-4 text-green-600 mt-0.5 shrink-0" />
                ) : (
                  <Circle className="size-4 text-muted-foreground mt-0.5 shrink-0" />
                )}
                <div>
                  <span className={`font-medium ${done ? 'line-through text-muted-foreground' : ''}`}>
                    {label}
                  </span>
                  {!done && (
                    <p className="text-xs text-muted-foreground mt-0.5">{detail}</p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
