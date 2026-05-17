'use client'

import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Brain,
  Loader2,
  RefreshCw,
  Trash2,
  Pencil,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
  Archive,
  Activity,
  ImageIcon,
  Settings2,
} from 'lucide-react'
import Link from 'next/link'
import { useBrand } from '@/lib/brand-context'

// ─── Types ────────────────────────────────────────────────────────────────────

type MemoryTier = 'core' | 'persistent' | 'standard' | 'transient'
type MemoryKind =
  | 'tone_rule'
  | 'principle'
  | 'gold_example'
  | 'discard_example'
  | 'brand_fact'
  | 'audience_insight'

interface MemoryFact {
  id: string
  kind: MemoryKind
  statement: string
  tier: MemoryTier
  importance: number
  asserted_at: string
  expires_at: string | null
  retrieval_hits: number
  last_retrieved: string | null
  source_kind: string | null
  source_id: string | null
  supersedes_id: string | null
  metadata: Record<string, unknown>
}

interface EpisodicEvent {
  event_kind: string
  subject_kind: string | null
  subject_id: string | null
  summary: string
  payload: Record<string, unknown>
  occurred_at: string
}

// ─── Constants ────────────────────────────────────────────────────────────────

const TIER_COLORS: Record<MemoryTier, string> = {
  core: 'bg-[var(--brand-primary)]/15 text-[var(--brand-primary)] border-[var(--brand-primary)]/30',
  persistent: 'status-info-soft border-[var(--status-info)]/30',
  standard: 'bg-[var(--surface-2)] text-ink-muted border-hairline',
  transient: 'status-warning-soft border-[var(--status-warning)]/30',
}

const KIND_COLORS: Record<MemoryKind, string> = {
  tone_rule: 'bg-[var(--surface-3)] text-ink-muted',
  principle: 'status-success-soft',
  gold_example: 'status-success-soft',
  discard_example: 'status-error-soft',
  brand_fact: 'status-info-soft',
  audience_insight: 'bg-[var(--brand-primary)]/10 text-[var(--brand-primary)]',
}

const TIER_OPTIONS: MemoryTier[] = ['core', 'persistent', 'standard', 'transient']
const KIND_OPTIONS: MemoryKind[] = [
  'tone_rule',
  'principle',
  'gold_example',
  'discard_example',
  'brand_fact',
  'audience_insight',
]

const EVENT_ICONS: Record<string, string> = {
  llm_call: '🤖',
  publish: '📣',
  feedback_bonus: '📊',
  writing_lab_vote: '🗳️',
  memory_consolidation: '🧠',
  memory_supersede: '🔄',
}

// ─── KPI Cards ────────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  icon: Icon,
  sub,
}: {
  label: string
  value: string | number
  icon: React.ComponentType<{ className?: string }>
  sub?: string
}) {
  return (
    <Card>
      <CardContent className="pt-4 pb-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-2xl font-bold mt-0.5">{value}</p>
            {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
          </div>
          <Icon className="size-8 text-muted-foreground/30" />
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Edit Dialog ──────────────────────────────────────────────────────────────

function EditDialog({
  fact,
  onClose,
  onSaved,
}: {
  fact: MemoryFact | null
  onClose: () => void
  onSaved: () => void
}) {
  const [statement, setStatement] = useState(fact?.statement || '')
  const [tier, setTier] = useState<MemoryTier>(fact?.tier || 'standard')
  const [importance, setImportance] = useState(String(fact?.importance ?? 0.5))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (fact) {
      setStatement(fact.statement)
      setTier(fact.tier)
      setImportance(String(fact.importance))
    }
  }, [fact])

  const handleSave = async () => {
    if (!fact) return
    setSaving(true)
    setError(null)
    try {
      const resp = await fetch(`/api/memory/facts/${fact.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          statement: statement.trim(),
          tier,
          importance: parseFloat(importance),
        }),
      })
      const json = await resp.json()
      if (json.success) {
        onSaved()
        onClose()
      } else {
        setError(json.error?.message || 'Save failed')
      }
    } catch {
      setError('Network error')
    }
    setSaving(false)
  }

  return (
    <Dialog open={!!fact} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Edit Memory Fact</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label className="text-xs">Statement</Label>
            <textarea
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
              rows={4}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Tier</Label>
              <Select value={tier} onValueChange={(v) => setTier((v ?? 'standard') as MemoryTier)}>
                <SelectTrigger className="h-8 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIER_OPTIONS.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Importance (0–1)</Label>
              <Input
                value={importance}
                onChange={(e) => setImportance(e.target.value)}
                type="number"
                min="0"
                max="1"
                step="0.05"
                className="h-8 text-sm"
              />
            </div>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
          <Button
            size="sm"
            disabled={saving || !statement.trim()}
            onClick={handleSave}
            className="bg-staging-bg hover:bg-staging-bg/90 text-white"
          >
            {saving ? <Loader2 className="size-3 animate-spin mr-1" /> : null}
            {saving ? 'Saving…' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Fact Row ─────────────────────────────────────────────────────────────────

function FactRow({
  fact,
  onEdit,
  onDelete,
  deleting,
}: {
  fact: MemoryFact
  onEdit: (f: MemoryFact) => void
  onDelete: (f: MemoryFact) => void
  deleting?: boolean
}) {
  const isExpiringSoon =
    fact.expires_at &&
    new Date(fact.expires_at).getTime() - Date.now() < 7 * 24 * 3600 * 1000

  return (
    <div className="py-3 border-b border-border last:border-0 flex gap-3 group">
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-1.5 mb-1">
          <Badge
            variant="outline"
            className={`text-[10px] px-1.5 py-0 ${KIND_COLORS[fact.kind]}`}
          >
            {fact.kind.replace(/_/g, ' ')}
          </Badge>
          <Badge
            variant="outline"
            className={`text-[10px] px-1.5 py-0 ${TIER_COLORS[fact.tier]}`}
          >
            {fact.tier}
          </Badge>
          <span className="text-[10px] text-muted-foreground">
            imp {fact.importance.toFixed(2)}
          </span>
          {fact.retrieval_hits > 0 && (
            <span className="text-[10px] text-muted-foreground">
              {fact.retrieval_hits} hits
            </span>
          )}
          {isExpiringSoon && (
            <span className="text-[10px] text-[var(--status-warning)] flex items-center gap-0.5">
              <AlertTriangle className="size-3" /> expiring
            </span>
          )}
        </div>
        <p className="text-sm leading-snug">{fact.statement}</p>
        <p className="text-[10px] text-muted-foreground mt-0.5">
          {new Date(fact.asserted_at).toLocaleDateString('en-GB', {
            day: '2-digit', month: 'short', year: 'numeric',
          })}
          {fact.source_kind && ` · source: ${fact.source_kind}`}
        </p>
      </div>
      <div className="flex items-start gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => onEdit(fact)}
          title="Edit"
        >
          <Pencil className="size-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-destructive hover:text-destructive"
          onClick={() => onDelete(fact)}
          disabled={deleting}
          title="Delete"
        >
          {deleting ? <Loader2 className="size-3.5 animate-spin" /> : <Trash2 className="size-3.5" />}
        </Button>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function MemoryInspectorPage() {
  const { activeBrand, isLoading: brandLoading } = useBrand()
  const [facts, setFacts] = useState<MemoryFact[]>([])
  const [events, setEvents] = useState<EpisodicEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [consolidating, setConsolidating] = useState(false)
  const [consolidateMsg, setConsolidateMsg] = useState<string | null>(null)

  // Filters
  const [filterKind, setFilterKind] = useState<string>('all')
  const [filterTier, setFilterTier] = useState<string>('all')

  // Edit / Delete
  const [editFact, setEditFact] = useState<MemoryFact | null>(null)
  // Was previously discarded ([, setDeletingId]); we now read it to disable
  // the delete button on the row currently being deleted (audit P2 #12).
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const kindParam = filterKind !== 'all' ? `&kind=${filterKind}` : ''
      const tierParam = filterTier !== 'all' ? `&tier=${filterTier}` : ''
      const [factsResp, eventsResp] = await Promise.all([
        fetch(`/api/memory/facts?limit=200${kindParam}${tierParam}`),
        fetch('/api/memory/episodic?limit=100'),
      ])
      const factsJson = await factsResp.json()
      const eventsJson = await eventsResp.json()
      if (factsJson.success) setFacts(factsJson.data || [])
      else setLoadError(factsJson?.error?.message || 'Could not load memory facts')
      if (eventsJson.success) setEvents(eventsJson.data || [])
    } catch {
      setLoadError('Network error loading memory')
    }
    setLoading(false)
  }, [filterKind, filterTier])

  useEffect(() => {
    if (!brandLoading) load()
  }, [load, brandLoading])

  const handleDelete = async (fact: MemoryFact) => {
    if (!confirm(`Delete fact?\n\n"${fact.statement.slice(0, 100)}…"`)) return
    setDeletingId(fact.id)
    setDeleteError(null)
    try {
      const resp = await fetch(`/api/memory/facts/${fact.id}`, { method: 'DELETE' })
      const json = await resp.json()
      if (json.success) {
        setFacts((prev) => prev.filter((f) => f.id !== fact.id))
      } else {
        setDeleteError(json?.error?.message || 'Delete failed')
      }
    } catch {
      setDeleteError('Network error — fact was not deleted')
    }
    setDeletingId(null)
  }

  const handleConsolidate = async () => {
    setConsolidating(true)
    setConsolidateMsg(null)
    try {
      const resp = await fetch('/api/memory/consolidate', { method: 'POST' })
      const json = await resp.json()
      if (json.success) {
        const d = json.data
        setConsolidateMsg(
          `✅ Done: +${d.facts_added} added, ${d.facts_rejected_verify} verify-failed, ${d.facts_rejected_dedup} deduped (${d.duration_s?.toFixed(1)}s)`
        )
        load()
      } else {
        setConsolidateMsg(`❌ ${json.error?.message || 'Consolidation failed'}`)
      }
    } catch {
      setConsolidateMsg('❌ Network error')
    }
    setConsolidating(false)
  }

  // ── KPI counters ────────────────────────────────────────────────────────────
  const countByTier = (t: MemoryTier) => facts.filter((f) => f.tier === t).length
  const expiringSoon = facts.filter(
    (f) =>
      f.expires_at &&
      new Date(f.expires_at).getTime() - Date.now() < 7 * 24 * 3600 * 1000
  ).length
  const avgAge =
    facts.length > 0
      ? Math.round(
          facts.reduce(
            (sum, f) =>
              sum +
              (Date.now() - new Date(f.asserted_at).getTime()) / 86400000,
            0
          ) / facts.length
        )
      : 0

  const filteredFacts =
    filterKind === 'all' && filterTier === 'all'
      ? facts
      : facts.filter(
          (f) =>
            (filterKind === 'all' || f.kind === filterKind) &&
            (filterTier === 'all' || f.tier === filterTier)
        )

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="size-6" /> Memory Inspector
          </h1>
          {activeBrand && (
            <p className="text-sm text-muted-foreground mt-0.5">
              {activeBrand.name}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/settings/brand-context"
            className="inline-flex items-center gap-1 h-7 px-2.5 text-xs rounded-lg
                       border hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
          >
            <Settings2 className="size-3" /> Brand Context
          </Link>
          <Link
            href="/settings/brand-assets"
            className="inline-flex items-center gap-1 h-7 px-2.5 text-xs rounded-lg
                       border hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
          >
            <ImageIcon className="size-3" /> Visual Assets
          </Link>
          {consolidateMsg && (
            <p className="text-xs text-muted-foreground max-w-xs text-right">{consolidateMsg}</p>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={handleConsolidate}
            disabled={consolidating}
            className="gap-1.5"
          >
            {consolidating ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Zap className="size-3.5" />
            )}
            {consolidating ? 'Consolidating…' : 'Consolidate'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={load}
            disabled={loading}
            className="gap-1.5"
          >
            <RefreshCw className={`size-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Surface load + delete errors before everything else so users notice */}
      {(loadError || deleteError) && (
        <div className="space-y-1">
          {loadError && (
            <p className="text-sm text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
              {loadError}
            </p>
          )}
          {deleteError && (
            <p className="text-sm text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2 flex items-center justify-between gap-2">
              <span>{deleteError}</span>
              <button
                onClick={() => setDeleteError(null)}
                className="text-xs underline shrink-0"
              >
                dismiss
              </button>
            </p>
          )}
        </div>
      )}

      {/* KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard label="Total facts" value={loading ? '—' : facts.length} icon={Brain} />
        <KpiCard
          label="Core / Persistent"
          value={loading ? '—' : `${countByTier('core')} / ${countByTier('persistent')}`}
          icon={CheckCircle}
          sub="never / 365d TTL"
        />
        <KpiCard
          label="Avg age"
          value={loading ? '—' : `${avgAge}d`}
          icon={Clock}
          sub={loading ? '' : `${countByTier('transient')} transient`}
        />
        <KpiCard
          label="Expiring ≤7d"
          value={loading ? '—' : expiringSoon}
          icon={AlertTriangle}
          sub={loading ? '' : expiringSoon > 0 ? 'review needed' : 'all good'}
        />
      </div>

      {/* Main content: facts + episodic feed side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Facts list (2/3 width) */}
        <div className="lg:col-span-2 space-y-3">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <CardTitle className="text-sm">
                  Semantic Facts
                  <Badge variant="secondary" className="ml-2 text-[10px]">
                    {filteredFacts.length}
                  </Badge>
                </CardTitle>
                <div className="flex items-center gap-2">
                  {/* Kind filter */}
                  <Select value={filterKind} onValueChange={(v) => setFilterKind(v ?? 'all')}>
                    <SelectTrigger className="h-7 text-xs w-36">
                      <SelectValue placeholder="All kinds" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All kinds</SelectItem>
                      {KIND_OPTIONS.map((k) => (
                        <SelectItem key={k} value={k}>
                          {k.replace(/_/g, ' ')}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {/* Tier filter */}
                  <Select value={filterTier} onValueChange={(v) => setFilterTier(v ?? 'all')}>
                    <SelectTrigger className="h-7 text-xs w-28">
                      <SelectValue placeholder="All tiers" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All tiers</SelectItem>
                      {TIER_OPTIONS.map((t) => (
                        <SelectItem key={t} value={t}>{t}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="size-6 animate-spin text-muted-foreground" />
                </div>
              ) : filteredFacts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground text-sm">
                  No memory facts yet. Run <strong>Consolidate</strong> to extract from
                  recent events, or add facts manually via{' '}
                  <Link href="/settings/brand-context" className="underline">Brand Context</Link>.
                </div>
              ) : (
                <div>
                  {filteredFacts.map((f) => (
                    <FactRow
                      key={f.id}
                      fact={f}
                      onEdit={setEditFact}
                      onDelete={handleDelete}
                      deleting={deletingId === f.id}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tier breakdown */}
          <div className="grid grid-cols-4 gap-2">
            {TIER_OPTIONS.map((t) => (
              <button
                key={t}
                onClick={() => setFilterTier(filterTier === t ? 'all' : t)}
                className={`rounded-md border px-2 py-1.5 text-xs font-medium transition-colors ${
                  TIER_COLORS[t]
                } ${filterTier === t ? 'ring-2 ring-offset-1 ring-brand-primary' : ''}`}
              >
                <Archive className="size-3 inline mr-1" />
                {t}
                <span className="ml-1 opacity-70">({countByTier(t)})</span>
              </button>
            ))}
          </div>
        </div>

        {/* Episodic feed (1/3 width) */}
        <div>
          <Card className="h-full">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Activity className="size-4 text-muted-foreground" />
                Episodic Feed
                <Badge variant="secondary" className="text-[10px]">
                  {events.length}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="size-6 animate-spin text-muted-foreground" />
                </div>
              ) : events.length === 0 ? (
                <p className="text-xs text-muted-foreground py-4 text-center">
                  No episodic events yet.
                </p>
              ) : (
                <div className="space-y-0">
                  {events.map((ev, i) => (
                    <div
                      key={i}
                      className="py-2.5 border-b border-border last:border-0"
                    >
                      <div className="flex items-start gap-2">
                        <span className="text-base leading-none mt-0.5 shrink-0">
                          {EVENT_ICONS[ev.event_kind] || '📌'}
                        </span>
                        <div className="min-w-0">
                          <p className="text-xs leading-snug truncate">{ev.summary}</p>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <Badge
                              variant="outline"
                              className="text-[9px] px-1 py-0 text-muted-foreground"
                            >
                              {ev.event_kind}
                            </Badge>
                            <span className="text-[9px] text-muted-foreground">
                              {new Date(ev.occurred_at).toLocaleString('en-GB', {
                                day: '2-digit',
                                month: 'short',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit dialog */}
      <EditDialog
        fact={editFact}
        onClose={() => setEditFact(null)}
        onSaved={load}
      />
    </div>
  )
}
