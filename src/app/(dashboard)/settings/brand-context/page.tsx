'use client'

/**
 * /settings/brand-context — P3.1
 * Focused view of brand identity memory facts (tone_rule, principle,
 * gold_example, discard_example) with inline edit, delete, and add-new-fact.
 */

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { BrandDiscovery } from '@/components/brand-context/brand-discovery'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Loader2, Pencil, Trash2, Check, X, ExternalLink, ChevronLeft, Rss, Plus, Sparkles } from 'lucide-react'
import { useBrand } from '@/lib/brand-context'
import { ContextDocumentUpload } from '@/components/brand-context/context-document-upload'

// ─── Types ────────────────────────────────────────────────────────────────────

type MemoryTier = 'core' | 'persistent' | 'standard' | 'transient'
type IdentityKind = 'tone_rule' | 'principle' | 'gold_example' | 'discard_example'

interface MemoryFact {
  id: string
  kind: IdentityKind
  statement: string
  tier: MemoryTier
  importance: number
  asserted_at: string
  expires_at: string | null
  retrieval_hits: number
}

// ─── Constants ────────────────────────────────────────────────────────────────

const IDENTITY_KINDS: IdentityKind[] = ['tone_rule', 'principle', 'gold_example', 'discard_example']

const KIND_META: Record<IdentityKind, { label: string; headerClass: string; badgeClass: string }> = {
  tone_rule: {
    label: 'Tone Rules',
    headerClass: 'bg-[var(--surface-2)] border-hairline',
    badgeClass: 'bg-[var(--surface-3)] text-ink-muted border-hairline',
  },
  principle: {
    label: 'Principles',
    headerClass: 'bg-[var(--status-success)]/5 border-[var(--status-success)]/20',
    badgeClass: 'status-success-soft border-[var(--status-success)]/30',
  },
  gold_example: {
    label: 'Gold Examples',
    headerClass: 'bg-[var(--brand-primary)]/5 border-[var(--brand-primary)]/20',
    badgeClass: 'bg-[var(--brand-primary)]/10 text-[var(--brand-primary)] border-[var(--brand-primary)]/30',
  },
  discard_example: {
    label: 'Discard Examples',
    headerClass: 'bg-[var(--status-error)]/5 border-[var(--status-error)]/20',
    badgeClass: 'status-error-soft border-[var(--status-error)]/30',
  },
}

const TIER_OPTIONS: MemoryTier[] = ['core', 'persistent', 'standard', 'transient']

// ─── Inline Edit Row ──────────────────────────────────────────────────────────

function FactRow({
  fact,
  onUpdated,
  onDeleted,
}: {
  fact: MemoryFact
  onUpdated: (updated: MemoryFact) => void
  onDeleted: (id: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [statement, setStatement] = useState(fact.statement)
  const [tier, setTier] = useState<MemoryTier>(fact.tier)
  const [importance, setImportance] = useState(fact.importance)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [rowError, setRowError] = useState<string | null>(null)

  const handleSave = async () => {
    setSaving(true)
    setRowError(null)
    try {
      const resp = await fetch(`/api/memory/facts/${fact.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ statement: statement.trim(), tier, importance }),
      })
      const json = await resp.json()
      if (json.success) {
        onUpdated({ ...fact, statement: statement.trim(), tier, importance })
        setEditing(false)
      } else {
        setRowError(json?.error?.message || 'Could not save changes')
      }
    } catch {
      setRowError('Network error — changes were not saved')
    }
    setSaving(false)
  }

  const handleDelete = async () => {
    if (!confirm(`Delete fact?\n\n"${fact.statement.slice(0, 120)}"`)) return
    setDeleting(true)
    setRowError(null)
    try {
      const resp = await fetch(`/api/memory/facts/${fact.id}`, { method: 'DELETE' })
      const json = await resp.json()
      if (json.success) onDeleted(fact.id)
      else setRowError(json?.error?.message || 'Could not delete the fact')
    } catch {
      setRowError('Network error — fact was not deleted')
    }
    setDeleting(false)
  }

  const handleCancel = () => {
    setStatement(fact.statement)
    setTier(fact.tier)
    setImportance(fact.importance)
    setEditing(false)
  }

  return (
    <div className="py-3 border-b border-border last:border-0 group">
      {rowError && (
        <p className="text-[11px] text-destructive mb-1.5">{rowError}</p>
      )}
      {editing ? (
        <div className="space-y-2">
          <textarea
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            rows={3}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            autoFocus
          />
          <div className="flex items-center gap-2 flex-wrap">
            <Select value={tier} onValueChange={(v) => setTier((v ?? 'standard') as MemoryTier)}>
              <SelectTrigger className="h-7 text-xs w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIER_OPTIONS.map((t) => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex items-center gap-1.5">
              <Label className="text-xs text-muted-foreground whitespace-nowrap">Imp</Label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={importance}
                onChange={(e) => setImportance(parseFloat(e.target.value))}
                className="w-20 accent-primary"
              />
              <span className="text-xs text-muted-foreground w-7 text-right">{importance.toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-1 ml-auto">
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleCancel}>
                <X className="size-3.5" />
              </Button>
              <Button
                size="icon"
                className="h-7 w-7"
                disabled={saving || !statement.trim()}
                onClick={handleSave}
              >
                {saving ? <Loader2 className="size-3 animate-spin" /> : <Check className="size-3.5" />}
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex gap-2">
          <div className="flex-1 min-w-0">
            <p
              className="text-sm leading-snug cursor-pointer hover:text-primary transition-colors"
              onClick={() => setEditing(true)}
              title="Click to edit"
            >
              {fact.statement}
            </p>
            <div className="flex items-center gap-1.5 mt-1 flex-wrap">
              <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${KIND_META[fact.kind].badgeClass}`}>
                {KIND_META[fact.kind].label}
              </Badge>
              <span className="text-[10px] text-muted-foreground">{fact.tier}</span>
              <span className="text-[10px] text-muted-foreground">imp {fact.importance.toFixed(2)}</span>
              {fact.retrieval_hits > 0 && (
                <span className="text-[10px] text-muted-foreground">{fact.retrieval_hits} hits</span>
              )}
            </div>
          </div>
          <div className="flex items-start gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setEditing(true)}
              title="Edit"
            >
              <Pencil className="size-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-destructive hover:text-destructive"
              onClick={handleDelete}
              disabled={deleting}
              title="Delete"
            >
              {deleting ? <Loader2 className="size-3 animate-spin" /> : <Trash2 className="size-3.5" />}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Add Fact Form ─────────────────────────────────────────────────────────────

function AddFactForm({
  kind,
  onAdded,
}: {
  kind: IdentityKind
  onAdded: (fact: MemoryFact) => void
}) {
  const [open, setOpen] = useState(false)
  const [statement, setStatement] = useState('')
  const [tier, setTier] = useState<MemoryTier>('standard')
  const [importance, setImportance] = useState(0.5)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSave = async () => {
    if (!statement.trim()) return
    setSaving(true)
    setError(null)
    try {
      const resp = await fetch('/api/memory/facts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, statement: statement.trim(), tier, importance }),
      })
      const json = await resp.json()
      if (json.success) {
        onAdded(json.data as MemoryFact)
        setStatement('')
        setTier('standard')
        setImportance(0.5)
        setOpen(false)
      } else {
        setError(json.error?.message || 'Failed to save')
      }
    } catch {
      setError('Network error')
    }
    setSaving(false)
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full text-left text-xs text-muted-foreground hover:text-foreground py-2 px-1 border border-dashed border-border rounded-md hover:border-primary/40 transition-colors flex items-center gap-1.5"
      >
        <span className="text-base leading-none">+</span> Add {KIND_META[kind].label.toLowerCase().replace(/s$/, '')}
      </button>
    )
  }

  return (
    <div className="space-y-2 p-3 bg-secondary/40 rounded-md border border-border">
      <textarea
        value={statement}
        onChange={(e) => setStatement(e.target.value)}
        rows={3}
        placeholder={`Enter a ${KIND_META[kind].label.toLowerCase().replace(/s$/, '')}…`}
        className="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        autoFocus
      />
      <div className="flex items-center gap-2 flex-wrap">
        <Select value={tier} onValueChange={(v) => setTier((v ?? 'standard') as MemoryTier)}>
          <SelectTrigger className="h-7 text-xs w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TIER_OPTIONS.map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex items-center gap-1.5">
          <Label className="text-xs text-muted-foreground whitespace-nowrap">Importance</Label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={importance}
            onChange={(e) => setImportance(parseFloat(e.target.value))}
            className="w-20 accent-primary"
          />
          <span className="text-xs text-muted-foreground w-7 text-right">{importance.toFixed(2)}</span>
        </div>
        <div className="flex items-center gap-1.5 ml-auto">
          <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            className="h-7 text-xs"
            disabled={saving || !statement.trim()}
            onClick={handleSave}
          >
            {saving ? <Loader2 className="size-3 animate-spin mr-1" /> : null}
            {saving ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

// ─── Kind Section ─────────────────────────────────────────────────────────────

function KindSection({
  kind,
  facts,
  onUpdated,
  onDeleted,
  onAdded,
}: {
  kind: IdentityKind
  facts: MemoryFact[]
  onUpdated: (f: MemoryFact) => void
  onDeleted: (id: string) => void
  onAdded: (f: MemoryFact) => void
}) {
  const meta = KIND_META[kind]
  return (
    <Card>
      <CardHeader className={`pb-2 rounded-t-lg ${meta.headerClass}`}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">{meta.label}</CardTitle>
          <Badge variant="secondary" className="text-[10px]">{facts.length}</Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        {facts.length === 0 ? (
          <p className="text-xs text-muted-foreground py-2">No {meta.label.toLowerCase()} yet.</p>
        ) : (
          <div>
            {facts.map((f) => (
              <FactRow key={f.id} fact={f} onUpdated={onUpdated} onDeleted={onDeleted} />
            ))}
          </div>
        )}
        <div className="mt-2">
          <AddFactForm kind={kind} onAdded={onAdded} />
        </div>
      </CardContent>
    </Card>
  )
}

// ─── RSS Feeds Card ───────────────────────────────────────────────────────────

interface RssFeed {
  url: string
  name: string
}

function RssFeedsCard({ brandId }: { brandId: string }) {
  const [feeds, setFeeds] = useState<RssFeed[]>([])
  // Cache the full research_sources object so we can merge-patch (preserve
  // every other key — web_sources, hashtags, …). Without this, replacing
  // research_sources.rss_feeds would silently wipe sibling settings.
  const [researchSources, setResearchSources] = useState<Record<string, unknown>>({})
  const [loading, setLoading] = useState(true)
  const [newUrl, setNewUrl] = useState('')
  const [newName, setNewName] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load feeds on mount by fetching full brands list and finding active brand
  useEffect(() => {
    async function loadFeeds() {
      setLoading(true)
      try {
        const resp = await fetch('/api/brands')
        const json = await resp.json()
        if (json.success && Array.isArray(json.data)) {
          const brand = json.data.find(
            (b: { id: string; research_sources?: Record<string, unknown> & { rss_feeds?: RssFeed[] } }) =>
              b.id === brandId,
          )
          const sources = (brand?.research_sources ?? {}) as Record<string, unknown> & { rss_feeds?: RssFeed[] }
          setResearchSources(sources)
          setFeeds(sources.rss_feeds ?? [])
        } else {
          setError('Could not load RSS feeds')
        }
      } catch {
        setError('Network error loading RSS feeds')
      }
      setLoading(false)
    }
    loadFeeds()
  }, [brandId])

  // Derive auto-name from URL hostname when name field is empty and url changes
  useEffect(() => {
    if (!newUrl) return
    try {
      const hostname = new URL(newUrl).hostname.replace(/^www\./, '')
      setNewName((prev) => (prev ? prev : hostname))
    } catch {
      // not a valid URL yet, leave name as-is
    }
  }, [newUrl])

  // Merge-patch: only research_sources.rss_feeds is replaced, every other key
  // under research_sources is preserved. Returns true on success.
  async function patchFeeds(updatedFeeds: RssFeed[]): Promise<boolean> {
    try {
      const merged = { ...researchSources, rss_feeds: updatedFeeds }
      const resp = await fetch(`/api/brands/${brandId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ research_sources: merged }),
      })
      if (!resp.ok) return false
      setResearchSources(merged)
      return true
    } catch {
      return false
    }
  }

  async function handleAdd() {
    const url = newUrl.trim()
    if (!url) return
    setError(null)
    // Basic URL validation
    try {
      new URL(url)
    } catch {
      setError('Please enter a valid URL (include https://)')
      return
    }
    if (feeds.some((f) => f.url === url)) {
      setError('This feed URL is already added')
      return
    }
    const name = newName.trim() || new URL(url).hostname.replace(/^www\./, '')
    const updated = [...feeds, { url, name }]
    const previous = feeds
    // Optimistic update
    setFeeds(updated)
    setNewUrl('')
    setNewName('')
    setAdding(true)
    const ok = await patchFeeds(updated)
    if (!ok) {
      setFeeds(previous) // roll back so the UI matches the server
      setError('Could not save the feed — try again')
    }
    setAdding(false)
  }

  async function handleDelete(url: string) {
    const previous = feeds
    const updated = feeds.filter((f) => f.url !== url)
    // Optimistic update
    setFeeds(updated)
    const ok = await patchFeeds(updated)
    if (!ok) {
      setFeeds(previous) // roll back
      setError('Could not delete the feed — try again')
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') handleAdd()
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Rss className="size-4 text-[var(--brand-primary)]" />
            RSS Feed Sources
          </CardTitle>
          <Badge variant="secondary" className="text-[10px]">{feeds.length}</Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          RSS feeds used by the research agent when generating content for this brand.
        </p>
      </CardHeader>
      <CardContent className="pt-2">
        {loading ? (
          <div className="flex justify-center py-4">
            <Loader2 className="size-4 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {feeds.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No RSS feeds added yet.</p>
            ) : (
              <div className="mb-3">
                {feeds.map((feed) => (
                  <div
                    key={feed.url}
                    className="flex items-center gap-2 py-2 border-b border-border last:border-0 group"
                  >
                    <Rss className="size-3.5 text-[var(--brand-primary)] shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{feed.name}</p>
                      <p className="text-[11px] text-muted-foreground truncate">{feed.url}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                      onClick={() => handleDelete(feed.url)}
                      title="Remove feed"
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {/* Add new feed form */}
            <div className="space-y-2 pt-1">
              <div className="flex gap-2">
                <div className="flex-1 min-w-0">
                  <Label className="text-xs text-muted-foreground mb-1 block">Feed URL</Label>
                  <Input
                    value={newUrl}
                    onChange={(e) => setNewUrl(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="https://example.com/feed.xml"
                    className="h-8 text-sm"
                  />
                </div>
                <div className="w-36 shrink-0">
                  <Label className="text-xs text-muted-foreground mb-1 block">Name (optional)</Label>
                  <Input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Auto-detected"
                    className="h-8 text-sm"
                  />
                </div>
                <div className="flex items-end shrink-0">
                  <Button
                    size="sm"
                    className="h-8 gap-1"
                    disabled={!newUrl.trim() || adding}
                    onClick={handleAdd}
                  >
                    {adding ? <Loader2 className="size-3 animate-spin" /> : <Plus className="size-3.5" />}
                    Add
                  </Button>
                </div>
              </div>
              {error && <p className="text-xs text-destructive">{error}</p>}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Brand Discovery Widget (thin wrapper to pass reload callback) ─────────────

function BrandDiscoveryWidget({ onSaved }: { onSaved: () => void }) {
  return <BrandDiscovery onFactsSaved={onSaved} />
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function BrandContextPage() {
  const { activeBrand, isLoading: brandLoading } = useBrand()
  const [facts, setFacts] = useState<MemoryFact[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const results = await Promise.all(
        IDENTITY_KINDS.map((kind) =>
          fetch(`/api/memory/facts?kind=${kind}&limit=200`).then((r) => r.json())
        )
      )
      const all: MemoryFact[] = []
      let anyFailed = false
      for (const r of results) {
        if (r.success) all.push(...(r.data as MemoryFact[]))
        else anyFailed = true
      }
      setFacts(all)
      if (anyFailed) setLoadError('Some memory categories failed to load — list may be partial')
    } catch {
      setLoadError('Could not load brand context. Try refreshing.')
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    if (!brandLoading) load()
  }, [load, brandLoading])

  const handleUpdated = (updated: MemoryFact) => {
    setFacts((prev) => prev.map((f) => (f.id === updated.id ? updated : f)))
  }

  const handleDeleted = (id: string) => {
    setFacts((prev) => prev.filter((f) => f.id !== id))
  }

  const handleAdded = (fact: MemoryFact) => {
    setFacts((prev) => [fact, ...prev])
  }

  const byKind = (kind: IdentityKind) => facts.filter((f) => f.kind === kind)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Link
            href="/settings"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft className="size-3.5" /> Settings
          </Link>
        </div>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold">Brand Context</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Brand identity facts loaded into memory for all AI agents
              {activeBrand && <span className="ml-1.5">· {activeBrand.name}</span>}
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0 mt-1">
            <Link
              href="/settings/brand-assets"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Visual Assets <ExternalLink className="size-3" />
            </Link>
            <Link
              href="/memory"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Full Memory Inspector <ExternalLink className="size-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* Content */}
      {loadError && (
        <p className="text-xs text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
          {loadError}
        </p>
      )}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-4">
          {/* Auto-discovery card — shown prominently when brand context is empty */}
          {facts.length === 0 && (
            <Card className="border-2 border-dashed border-primary/30 bg-primary/5">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Sparkles className="size-4 text-primary" />
                  Auto-Discover Brand Voice
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  Paste your website URL and let AI extract your brand tone, principles, and examples automatically.
                </p>
              </CardHeader>
              <CardContent>
                <BrandDiscoveryWidget onSaved={load} />
              </CardContent>
            </Card>
          )}
          {IDENTITY_KINDS.map((kind) => (
            <KindSection
              key={kind}
              kind={kind}
              facts={byKind(kind)}
              onUpdated={handleUpdated}
              onDeleted={handleDeleted}
              onAdded={handleAdded}
            />
          ))}
          {activeBrand && <RssFeedsCard brandId={activeBrand.id} />}
          {activeBrand && (
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Sparkles className="size-4 text-[var(--brand-primary)]" />
                    AI Context Ingest
                  </CardTitle>
                  <span className="text-[11px] text-muted-foreground">
                    Karpathy-wiki style · LLM-extracted
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Drop a brand document or paste a URL. The AI extracts candidate facts
                  (tone rules, principles, gold/discard examples) for review, then merges
                  the approved ones into the brand wiki every agent reads.
                </p>
              </CardHeader>
              <CardContent className="pt-2">
                <ContextDocumentUpload onIngested={load} />
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
