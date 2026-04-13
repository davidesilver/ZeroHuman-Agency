'use client'

import { useCallback, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { DraftCard } from '@/components/content/draft-card'
import { Button } from '@/components/ui/button'
import { LinkIcon, Loader2, Search } from 'lucide-react'

const STATUS_TABS = [
  { key: 'all', label: 'ALL' },
  { key: 'draft', label: 'DRAFTS' },
  { key: 'in_review', label: 'IN REVIEW' },
  { key: 'god_mode', label: 'GOD MODE' },
  { key: 'approved', label: 'APPROVED' },
  { key: 'scheduled', label: 'SCHEDULED' },
  { key: 'published', label: 'PUBLISHED' },
  { key: 'archived', label: 'ARCHIVED' },
] as const

export default function ContentHubPage() {
  const [drafts, setDrafts] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState('all')
  const [isLoading, setIsLoading] = useState(true)
  const [urlInput, setUrlInput] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeResult, setAnalyzeResult] = useState<string | null>(null)

  const fetchDrafts = useCallback(async () => {
    setIsLoading(true)
    const params = new URLSearchParams({ per_page: '50' })
    if (activeTab !== 'all') params.set('status', activeTab)
    try {
      const resp = await fetch(`/api/content/drafts?${params}`)
      const json = await resp.json()
      if (json.success) setDrafts(json.data.drafts || json.data || [])
    } catch {}
    setIsLoading(false)
  }, [activeTab])

  useEffect(() => { fetchDrafts() }, [fetchDrafts])

  const handleAnalyzeUrl = async () => {
    if (!urlInput.trim()) return
    setAnalyzing(true)
    setAnalyzeResult(null)
    try {
      const resp = await fetch('/api/content/from-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlInput.trim() }),
      })
      const json = await resp.json()
      if (json.success) {
        setAnalyzeResult('✅ URL added to research pipeline. Scoring will run automatically.')
        setUrlInput('')
        // Refresh drafts after a moment (scoring + generation may take time)
        setTimeout(fetchDrafts, 2000)
      } else {
        setAnalyzeResult(`❌ ${json.error?.message || 'Failed to analyze URL'}`)
      }
    } catch {
      setAnalyzeResult('❌ Failed to connect to backend')
    }
    setAnalyzing(false)
  }

  const handleAction = async (id: string, action: string) => {
    if (action === 'god_mode') {
      await fetch(`/api/content/drafts/${id}/god-mode`, { method: 'POST' })
    } else {
      await fetch(`/api/content/drafts/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: action }),
      })
    }
    fetchDrafts()
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Content Hub</h1>

      {/* URL Paste Input — Core Montemagno flow */}
      <div className="rounded-lg border border-border bg-secondary/30 p-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-muted-foreground">
            <LinkIcon className="size-4" />
          </div>
          <input
            type="url"
            value={urlInput}
            onChange={e => setUrlInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAnalyzeUrl()}
            placeholder="Paste a URL to analyze — AI will generate content from it..."
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/60"
          />
          <Button
            onClick={handleAnalyzeUrl}
            disabled={analyzing || !urlInput.trim()}
            className="bg-staging-bg hover:bg-staging-bg/90 text-white"
            size="sm"
          >
            {analyzing ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Search className="size-4" />
            )}
            {analyzing ? 'Analyzing...' : 'ANALYZE'}
          </Button>
        </div>
        {analyzeResult && (
          <p className="text-xs mt-2 text-muted-foreground">{analyzeResult}</p>
        )}
      </div>

      {/* Status Tabs */}
      <div className="flex gap-1 border-b border-border overflow-x-auto">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'px-3 py-2 text-xs font-medium whitespace-nowrap transition-colors border-b-2',
              activeTab === tab.key
                ? 'border-brand-primary text-brand-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading...</div>
      ) : drafts.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          No content found. Paste a URL above or generate content from the Research page.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {drafts.map((draft) => (
            <DraftCard key={draft.id} draft={draft} onAction={handleAction} />
          ))}
        </div>
      )}
    </div>
  )
}
