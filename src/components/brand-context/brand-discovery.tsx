'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Sparkles, Plus, X, Check, Loader2, AlertCircle, ChevronRight, Globe, LayoutGrid
} from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

type FactKind = 'tone_rule' | 'principle' | 'gold_example' | 'discard_example'

interface DiscoveredFact {
  kind: FactKind
  statement: string
  confidence: number
  source_url?: string
  selected: boolean
  editing: boolean
  editValue: string
}

interface DiscoveryResponse {
  facts: Array<{ kind: FactKind; statement: string; confidence: number }>
  suggested_topics: string[]
  scrape_errors: string[]
}

const KIND_META: Record<FactKind, { label: string; color: string; badgeClass: string }> = {
  tone_rule:       { label: 'Tone Rules',       color: 'bg-indigo-50 border-indigo-100', badgeClass: 'bg-indigo-100 text-indigo-700' },
  principle:       { label: 'Principles',        color: 'bg-green-50 border-green-100',  badgeClass: 'bg-green-100 text-green-700'  },
  gold_example:    { label: 'Gold Examples',     color: 'bg-emerald-50 border-emerald-100', badgeClass: 'bg-emerald-100 text-emerald-700' },
  discard_example: { label: 'Discard Examples',  color: 'bg-red-50 border-red-100',      badgeClass: 'bg-red-100 text-red-700'     },
}

const KINDS: FactKind[] = ['tone_rule', 'principle', 'gold_example', 'discard_example']

// ── Template types ─────────────────────────────────────────────────────────────

interface BrandTemplate {
  id: string
  name: string
  description: string
  emoji: string
  tone_rules: Array<{ statement: string; confidence: number }>
  principles: Array<{ statement: string; confidence: number }>
  gold_examples: Array<{ statement: string; confidence: number }>
  discard_examples: Array<{ statement: string; confidence: number }>
  suggested_topics: string[]
}

// ── Component ─────────────────────────────────────────────────────────────────

interface BrandDiscoveryProps {
  onFactsSaved?: (count: number) => void
}

type Tab = 'discover' | 'template'

export function BrandDiscovery({ onFactsSaved }: BrandDiscoveryProps) {
  const [tab, setTab] = useState<Tab>('discover')
  const [step, setStep] = useState<'input' | 'loading' | 'review' | 'saving' | 'done'>('input')
  const [urls, setUrls] = useState<string[]>([''])
  const [facts, setFacts] = useState<DiscoveredFact[]>([])
  const [suggestedTopics, setSuggestedTopics] = useState<string[]>([])
  const [scrapeErrors, setScrapeErrors] = useState<string[]>([])
  const [saveError, setSaveError] = useState<string | null>(null)
  const [savedCount, setSavedCount] = useState(0)
  const [templates, setTemplates] = useState<BrandTemplate[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(false)

  useEffect(() => {
    if (tab === 'template' && templates.length === 0) {
      setTemplatesLoading(true)
      fetch('/api/brand-templates')
        .then(r => r.json())
        .then(json => { if (json.success) setTemplates(json.data || []) })
        .catch(() => {})
        .finally(() => setTemplatesLoading(false))
    }
  }, [tab, templates.length])

  function loadTemplate(template: BrandTemplate) {
    const toFacts = (items: Array<{ statement: string; confidence: number }>, kind: FactKind): DiscoveredFact[] =>
      items.map(item => ({
        kind,
        statement: item.statement,
        confidence: item.confidence,
        selected: true,
        editing: false,
        editValue: item.statement,
      }))

    setFacts([
      ...toFacts(template.tone_rules, 'tone_rule'),
      ...toFacts(template.principles, 'principle'),
      ...toFacts(template.gold_examples, 'gold_example'),
      ...toFacts(template.discard_examples, 'discard_example'),
    ])
    setSuggestedTopics(template.suggested_topics || [])
    setScrapeErrors([])
    setStep('review')
  }

  // ── URL input management ───────────────────────────────────────────────────

  function addUrl() {
    setUrls(prev => [...prev, ''])
  }

  function removeUrl(i: number) {
    setUrls(prev => prev.filter((_, idx) => idx !== i))
  }

  function setUrl(i: number, val: string) {
    setUrls(prev => prev.map((u, idx) => idx === i ? val : u))
  }

  // ── Discovery call ─────────────────────────────────────────────────────────

  async function runDiscovery() {
    const validUrls = urls.map(u => u.trim()).filter(Boolean)
    if (validUrls.length === 0) return

    setStep('loading')
    setScrapeErrors([])
    setSaveError(null)

    try {
      const resp = await fetch('/api/brand-discovery', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls: validUrls }),
      })
      const json: { success: boolean; data?: DiscoveryResponse; error?: { message: string } } = await resp.json()

      if (!json.success || !json.data) {
        setScrapeErrors([json.error?.message || 'Discovery failed'])
        setStep('input')
        return
      }

      const { facts: rawFacts, suggested_topics, scrape_errors } = json.data
      setScrapeErrors(scrape_errors || [])
      setSuggestedTopics(suggested_topics || [])
      setFacts(rawFacts.map(f => ({
        ...f,
        selected: f.confidence >= 0.6,
        editing: false,
        editValue: f.statement,
      })))
      setStep('review')
    } catch {
      setScrapeErrors(['Network error — could not reach the backend'])
      setStep('input')
    }
  }

  // ── Review actions ─────────────────────────────────────────────────────────

  function toggleSelect(i: number) {
    setFacts(prev => prev.map((f, idx) => idx === i ? { ...f, selected: !f.selected } : f))
  }

  function startEdit(i: number) {
    setFacts(prev => prev.map((f, idx) => idx === i ? { ...f, editing: true, editValue: f.statement } : f))
  }

  function commitEdit(i: number) {
    setFacts(prev => prev.map((f, idx) =>
      idx === i ? { ...f, editing: false, statement: f.editValue.trim() || f.statement } : f
    ))
  }

  function setEditValue(i: number, val: string) {
    setFacts(prev => prev.map((f, idx) => idx === i ? { ...f, editValue: val } : f))
  }

  function removeFact(i: number) {
    setFacts(prev => prev.filter((_, idx) => idx !== i))
  }

  // ── Save selected facts ────────────────────────────────────────────────────

  async function saveSelected() {
    const selected = facts.filter(f => f.selected)
    if (selected.length === 0) return

    setStep('saving')
    setSaveError(null)
    let saved = 0
    const errors: string[] = []

    for (const fact of selected) {
      try {
        const resp = await fetch('/api/memory/facts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            kind: fact.kind,
            statement: fact.statement,
            tier: fact.confidence >= 0.85 ? 'persistent' : 'standard',
            importance: Math.min(fact.confidence, 0.9),
          }),
        })
        const json = await resp.json()
        if (json.success) {
          saved++
        } else {
          errors.push(fact.statement.slice(0, 60))
        }
      } catch {
        errors.push(fact.statement.slice(0, 60))
      }
    }

    setSavedCount(saved)
    if (errors.length > 0) {
      setSaveError(`${errors.length} fact(s) could not be saved.`)
    }
    onFactsSaved?.(saved)
    setStep('done')
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (step === 'done') {
    return (
      <div className="text-center py-8 space-y-3">
        <div className="flex justify-center">
          <div className="size-12 rounded-full bg-green-100 flex items-center justify-center">
            <Check className="size-6 text-green-600" />
          </div>
        </div>
        <p className="font-medium text-sm">{savedCount} fact{savedCount !== 1 ? 's' : ''} saved to brand context</p>
        {saveError && <p className="text-xs text-amber-600">{saveError}</p>}
        {suggestedTopics.length > 0 && (
          <div className="mt-4 text-left">
            <p className="text-xs text-muted-foreground mb-2">Suggested research topics:</p>
            <div className="flex flex-wrap gap-1.5">
              {suggestedTopics.map(t => (
                <Badge key={t} variant="outline" className="text-xs">{t}</Badge>
              ))}
            </div>
          </div>
        )}
        <Button variant="outline" size="sm" onClick={() => { setStep('input'); setFacts([]); setUrls(['']) }}>
          Run again
        </Button>
      </div>
    )
  }

  if (step === 'loading') {
    return (
      <div className="text-center py-12 space-y-3">
        <Loader2 className="size-8 animate-spin mx-auto text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Analyzing brand voice…</p>
        <p className="text-xs text-muted-foreground">Scraping content and running AI analysis</p>
      </div>
    )
  }

  if (step === 'saving') {
    return (
      <div className="text-center py-12 space-y-3">
        <Loader2 className="size-8 animate-spin mx-auto text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Saving brand context…</p>
      </div>
    )
  }

  if (step === 'review') {
    const selectedCount = facts.filter(f => f.selected).length

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Review extracted brand voice</p>
            <p className="text-xs text-muted-foreground">{selectedCount} of {facts.length} facts selected</p>
          </div>
          <Button
            size="sm"
            onClick={saveSelected}
            disabled={selectedCount === 0}
          >
            <Check className="size-3.5 mr-1.5" />
            Save {selectedCount} fact{selectedCount !== 1 ? 's' : ''}
          </Button>
        </div>

        {scrapeErrors.length > 0 && (
          <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-2.5">
            <AlertCircle className="size-3.5 mt-0.5 shrink-0" />
            <span>{scrapeErrors.length} URL(s) had issues: {scrapeErrors[0]}</span>
          </div>
        )}

        {KINDS.map(kind => {
          const kindFacts = facts.map((f, i) => ({ ...f, _i: i })).filter(f => f.kind === kind)
          if (kindFacts.length === 0) return null
          const meta = KIND_META[kind]
          return (
            <Card key={kind} className={`border ${meta.color}`}>
              <CardHeader className="py-2.5 px-4">
                <CardTitle className="text-xs font-medium flex items-center gap-2">
                  <span>{meta.label}</span>
                  <Badge className={`text-[11px] ${meta.badgeClass} border-0`}>{kindFacts.length}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-3 space-y-2">
                {kindFacts.map(({ _i, selected, editing, editValue, statement, confidence }) => (
                  <div key={_i} className={`flex gap-2 items-start rounded-md p-2 transition-colors ${selected ? 'bg-white' : 'bg-muted/30 opacity-60'}`}>
                    <button
                      className={`mt-0.5 size-4 rounded border flex-shrink-0 flex items-center justify-center transition-colors ${selected ? 'bg-primary border-primary text-white' : 'border-border'}`}
                      onClick={() => toggleSelect(_i)}
                    >
                      {selected && <Check className="size-2.5" />}
                    </button>

                    <div className="flex-1 min-w-0">
                      {editing ? (
                        <div className="flex gap-1.5 items-start">
                          <Input
                            value={editValue}
                            onChange={e => setEditValue(_i, e.target.value)}
                            className="text-xs h-7 flex-1"
                            autoFocus
                            onKeyDown={e => { if (e.key === 'Enter') commitEdit(_i) }}
                          />
                          <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => commitEdit(_i)}>
                            <Check className="size-3" />
                          </Button>
                        </div>
                      ) : (
                        <button className="text-xs text-left w-full hover:text-primary" onClick={() => startEdit(_i)}>
                          {statement}
                        </button>
                      )}
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[11px] text-muted-foreground">
                          confidence {Math.round(confidence * 100)}%
                        </span>
                      </div>
                    </div>

                    <button
                      className="mt-0.5 text-muted-foreground hover:text-destructive transition-colors shrink-0"
                      onClick={() => removeFact(_i)}
                    >
                      <X className="size-3.5" />
                    </button>
                  </div>
                ))}
              </CardContent>
            </Card>
          )
        })}

        <Button variant="ghost" size="sm" onClick={() => setStep('input')} className="w-full text-muted-foreground">
          ← Back to URLs
        </Button>
      </div>
    )
  }

  // step === 'input'
  return (
    <div className="space-y-4">
      {/* Tab switcher */}
      <div className="flex rounded-md border border-border overflow-hidden text-xs">
        <button
          className={`flex-1 py-1.5 px-3 flex items-center justify-center gap-1.5 transition-colors ${tab === 'discover' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
          onClick={() => setTab('discover')}
        >
          <Sparkles className="size-3" /> Auto-Discover
        </button>
        <button
          className={`flex-1 py-1.5 px-3 flex items-center justify-center gap-1.5 transition-colors ${tab === 'template' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
          onClick={() => setTab('template')}
        >
          <LayoutGrid className="size-3" /> Use Template
        </button>
      </div>

      {/* Template picker */}
      {tab === 'template' && (
        <div>
          {templatesLoading ? (
            <div className="flex justify-center py-6"><Loader2 className="size-5 animate-spin text-muted-foreground" /></div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              {templates.map(t => (
                <button
                  key={t.id}
                  className="text-left rounded-md border border-border p-3 hover:border-primary hover:bg-primary/5 transition-colors"
                  onClick={() => loadTemplate(t)}
                >
                  <div className="text-base mb-0.5">{t.emoji}</div>
                  <div className="text-xs font-medium">{t.name}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5 leading-tight">{t.description}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* URL input — only shown on discover tab */}
      {tab === 'discover' && (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            Enter your website and/or social profile URLs. The AI will analyze the content and extract your brand voice automatically.
          </p>
          {urls.map((url, i) => (
            <div key={i} className="flex gap-2">
              <div className="relative flex-1">
                <Globe className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                <Input
                  value={url}
                  onChange={e => setUrl(i, e.target.value)}
                  placeholder="https://yoursite.com"
                  className="pl-8 text-sm h-8"
                  onKeyDown={e => { if (e.key === 'Enter') addUrl() }}
                />
              </div>
              {urls.length > 1 && (
                <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground" onClick={() => removeUrl(i)}>
                  <X className="size-3.5" />
                </Button>
              )}
            </div>
          ))}
          {urls.length < 8 && (
            <Button variant="ghost" size="sm" className="text-xs text-muted-foreground h-7 px-2" onClick={addUrl}>
              <Plus className="size-3 mr-1" /> Add URL
            </Button>
          )}
          {scrapeErrors.length > 0 && (
            <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-2.5">
              <AlertCircle className="size-3.5 mt-0.5 shrink-0" />
              <span>{scrapeErrors[0]}</span>
            </div>
          )}
          <Button
            className="w-full"
            onClick={runDiscovery}
            disabled={!urls.some(u => u.trim())}
          >
            <Sparkles className="size-3.5 mr-2" />
            Analyze Brand Voice
            <ChevronRight className="size-3.5 ml-auto" />
          </Button>
        </div>
      )}
    </div>
  )
}
