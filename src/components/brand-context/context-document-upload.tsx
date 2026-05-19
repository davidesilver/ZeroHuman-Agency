'use client'

/**
 * ContextDocumentUpload — Karpathy-wiki-style brand context ingestion.
 *
 * Flow (no data is written until the user confirms):
 *   1. User picks a .txt/.md/.pdf/.docx file *or* pastes a URL.
 *   2. We POST to /api/memory/upload (file) or /api/memory/discover (URL).
 *      Both endpoints proxy to the Python backend, which runs the doc through
 *      an LLM extractor and returns *candidate* memory facts (kind +
 *      statement + tier + importance + verifier outcome).
 *   3. The user reviews the candidates: edit text, change kind, drop unwanted
 *      ones, then click "Save N facts". We bulk-create them via
 *      /api/memory/facts so they're picked up by every agent on the next run.
 *
 * This is intentionally separate from /settings/brand-assets — assets are
 * binary creative (logos, palettes, design PDFs); context is *textual brand
 * identity* (tone, principles, do/don't examples, brand facts).
 */

import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Loader2, Upload, Link as LinkIcon, Sparkles,
  Trash2, AlertTriangle, CheckCircle2, FileText,
} from 'lucide-react'

type FactKind =
  | 'tone_rule'
  | 'principle'
  | 'gold_example'
  | 'discard_example'
  | 'brand_fact'
  | 'audience_insight'

type FactTier = 'core' | 'persistent' | 'standard' | 'transient'

interface Candidate {
  // local UI id — stable across edits & deletions
  _uid: string
  statement: string
  kind: FactKind
  tier: FactTier
  importance: number
  verified: boolean
  verification_failures?: string[]
  // bookkeeping for "x of N saved"
  _saving?: boolean
  _saved?: boolean
  _error?: string | null
}

const KIND_OPTIONS: FactKind[] = [
  'tone_rule', 'principle', 'gold_example', 'discard_example',
  'brand_fact', 'audience_insight',
]
const TIER_OPTIONS: FactTier[] = ['standard', 'persistent', 'core', 'transient']

const KIND_LABEL: Record<FactKind, string> = {
  tone_rule:        'Tone rule',
  principle:        'Principle',
  gold_example:     'Gold example',
  discard_example:  'Discard example',
  brand_fact:       'Brand fact',
  audience_insight: 'Audience insight',
}

const KIND_BADGE: Record<FactKind, string> = {
  tone_rule:        'bg-indigo-50 text-indigo-700 border-indigo-200',
  principle:        'bg-green-50 text-green-700 border-green-200',
  gold_example:     'bg-emerald-50 text-emerald-700 border-emerald-200',
  discard_example:  'bg-red-50 text-red-700 border-red-200',
  brand_fact:       'bg-sky-50 text-sky-700 border-sky-200',
  audience_insight: 'bg-amber-50 text-amber-700 border-amber-200',
}

let _uidCounter = 0
const nextUid = () => `c${++_uidCounter}_${Date.now()}`

// ─── Component ────────────────────────────────────────────────────────────────

export function ContextDocumentUpload({ onIngested }: { onIngested?: () => void }) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [file, setFile] = useState<File | null>(null)
  const [url, setUrl] = useState('')
  const [mode, setMode] = useState<'file' | 'url'>('file')

  const [extracting, setExtracting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sourceLabel, setSourceLabel] = useState<string | null>(null)

  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [savingAll, setSavingAll] = useState(false)
  const [savedCount, setSavedCount] = useState<number | null>(null)

  // ── Step 1: extract candidates from file or URL ───────────────────────────
  async function handleExtract() {
    setError(null)
    setSavedCount(null)
    setCandidates([])
    setExtracting(true)

    try {
      let resp: Response
      let label = ''

      if (mode === 'file') {
        if (!file) {
          setError('Pick a file first (.txt, .md, .pdf, .docx)')
          setExtracting(false)
          return
        }
        const fd = new FormData()
        fd.append('file', file)
        resp = await fetch('/api/memory/upload', { method: 'POST', body: fd })
        label = file.name
      } else {
        if (!url.trim()) {
          setError('Paste a URL first')
          setExtracting(false)
          return
        }
        resp = await fetch('/api/memory/discover', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: url.trim() }),
        })
        label = url.trim()
      }

      const json = await resp.json()
      if (!resp.ok || !json.success) {
        const msg = json?.error?.message || json?.detail || `Extraction failed (${resp.status})`
        setError(msg)
        setExtracting(false)
        return
      }

      // Normalize the candidate list. Both endpoints return
      // { data: { candidates: [...], count } } via the success envelope.
      const raw = (json.data?.candidates ?? []) as Array<{
        statement: string
        kind?: string
        tier?: string
        importance?: number
        verified?: boolean
        verification_failures?: string[]
      }>

      if (raw.length === 0) {
        setError('No facts could be extracted from this document. Try a richer source.')
        setExtracting(false)
        return
      }

      const normalized: Candidate[] = raw.map(c => ({
        _uid: nextUid(),
        statement: (c.statement || '').trim(),
        kind: (KIND_OPTIONS.includes(c.kind as FactKind) ? c.kind : 'brand_fact') as FactKind,
        tier: (TIER_OPTIONS.includes(c.tier as FactTier) ? c.tier : 'standard') as FactTier,
        importance: typeof c.importance === 'number' ? c.importance : 0.5,
        verified: c.verified !== false,
        verification_failures: c.verification_failures ?? [],
      })).filter(c => c.statement.length > 0)

      setCandidates(normalized)
      setSourceLabel(label)
    } catch {
      setError('Network error while extracting facts')
    }
    setExtracting(false)
  }

  // ── Candidate edits ───────────────────────────────────────────────────────
  function patchCandidate(uid: string, patch: Partial<Candidate>) {
    setCandidates(prev => prev.map(c => c._uid === uid ? { ...c, ...patch } : c))
  }
  function removeCandidate(uid: string) {
    setCandidates(prev => prev.filter(c => c._uid !== uid))
  }

  // ── Step 2: persist accepted candidates as memory facts ──────────────────
  async function handleSaveAll() {
    setSavingAll(true)
    let ok = 0
    const updated: Candidate[] = []

    for (const c of candidates) {
      if (c._saved) { updated.push(c); continue }
      try {
        const resp = await fetch('/api/memory/facts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            kind: c.kind,
            statement: c.statement.trim(),
            tier: c.tier,
            importance: c.importance,
          }),
        })
        const json = await resp.json()
        if (resp.ok && json.success) {
          ok++
          updated.push({ ...c, _saved: true, _error: null })
        } else {
          updated.push({ ...c, _error: json?.error?.message || 'save failed' })
        }
      } catch {
        updated.push({ ...c, _error: 'network error' })
      }
    }

    setCandidates(updated)
    setSavedCount(ok)
    setSavingAll(false)
    if (ok > 0) onIngested?.()
  }

  function reset() {
    setFile(null)
    setUrl('')
    setCandidates([])
    setSourceLabel(null)
    setError(null)
    setSavedCount(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const acceptedCount = candidates.filter(c => !c._saved).length

  return (
    <div className="space-y-3">
      {/* ── Source picker ─────────────────────────────────────────────── */}
      <div className="flex gap-1 text-xs">
        <button
          onClick={() => setMode('file')}
          className={`px-3 py-1.5 rounded-md transition-colors ${
            mode === 'file'
              ? 'bg-secondary text-foreground'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Upload className="size-3 inline mr-1" /> Upload file
        </button>
        <button
          onClick={() => setMode('url')}
          className={`px-3 py-1.5 rounded-md transition-colors ${
            mode === 'url'
              ? 'bg-secondary text-foreground'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <LinkIcon className="size-3 inline mr-1" /> From URL
        </button>
      </div>

      {/* ── File / URL input ──────────────────────────────────────────── */}
      <div className="flex flex-wrap items-end gap-2">
        {mode === 'file' ? (
          <div className="flex-1 min-w-[260px] space-y-1">
            <Label className="text-xs text-muted-foreground">
              Document <span className="opacity-60">(.txt, .md, .pdf, .docx — max ~12k characters extracted)</span>
            </Label>
            <Input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.pdf,.docx,text/plain,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="h-9 text-sm file:mr-3 file:rounded-sm file:border-0 file:bg-secondary file:px-2 file:py-1 file:text-xs"
            />
          </div>
        ) : (
          <div className="flex-1 min-w-[260px] space-y-1">
            <Label className="text-xs text-muted-foreground">
              URL <span className="opacity-60">(article, landing page, doc — extracted server-side)</span>
            </Label>
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/about"
              className="h-9 text-sm"
            />
          </div>
        )}

        <Button
          size="sm"
          className="h-9 gap-1.5"
          disabled={extracting || (mode === 'file' ? !file : !url.trim())}
          onClick={handleExtract}
        >
          {extracting
            ? <Loader2 className="size-3.5 animate-spin" />
            : <Sparkles className="size-3.5" />}
          {extracting ? 'Extracting…' : 'Extract facts'}
        </Button>
      </div>

      {error && (
        <div className="flex items-start gap-2 text-xs text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-2.5 py-2">
          <AlertTriangle className="size-3.5 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ── Candidate review ──────────────────────────────────────────── */}
      {candidates.length > 0 && (
        <div className="space-y-2 border border-border rounded-md p-3 bg-secondary/20">
          <div className="flex items-center gap-2 flex-wrap">
            <FileText className="size-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground truncate flex-1">
              From <span className="font-mono">{sourceLabel}</span>
            </span>
            <Badge variant="secondary" className="text-[11px]">
              {candidates.length} candidate{candidates.length === 1 ? '' : 's'}
            </Badge>
          </div>

          <p className="text-[11px] text-muted-foreground">
            Review the AI-extracted facts. Edit anything that&apos;s off. Discard
            what you don&apos;t want. Then save — they become part of the brand
            wiki every agent reads.
          </p>

          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {candidates.map(c => (
              <CandidateRow
                key={c._uid}
                candidate={c}
                onPatch={(patch) => patchCandidate(c._uid, patch)}
                onRemove={() => removeCandidate(c._uid)}
              />
            ))}
          </div>

          <div className="flex items-center justify-between gap-2 pt-2 border-t border-border">
            <span className="text-xs text-muted-foreground">
              {savedCount != null
                ? `Saved ${savedCount} of ${candidates.length}.`
                : `${acceptedCount} ready to save`}
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="h-8 text-xs" onClick={reset}>
                Clear
              </Button>
              <Button
                size="sm"
                className="h-8 text-xs gap-1.5"
                disabled={savingAll || acceptedCount === 0}
                onClick={handleSaveAll}
              >
                {savingAll
                  ? <Loader2 className="size-3 animate-spin" />
                  : <CheckCircle2 className="size-3" />}
                {savingAll ? 'Saving…' : `Save ${acceptedCount} fact${acceptedCount === 1 ? '' : 's'}`}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Candidate row ────────────────────────────────────────────────────────────

function CandidateRow({
  candidate,
  onPatch,
  onRemove,
}: {
  candidate: Candidate
  onPatch: (patch: Partial<Candidate>) => void
  onRemove: () => void
}) {
  const c = candidate

  if (c._saved) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-green-50 border border-green-200 text-xs">
        <CheckCircle2 className="size-3.5 text-green-600 shrink-0" />
        <span className="flex-1 truncate text-green-900">{c.statement}</span>
        <Badge variant="outline" className={`text-[11px] ${KIND_BADGE[c.kind]}`}>
          {KIND_LABEL[c.kind]}
        </Badge>
      </div>
    )
  }

  return (
    <div className={`rounded-md border bg-background p-2.5 space-y-2 ${
      c._error ? 'border-destructive/40' : 'border-border'
    }`}>
      <textarea
        value={c.statement}
        onChange={(e) => onPatch({ statement: e.target.value })}
        rows={2}
        className="w-full text-sm bg-transparent resize-none focus:outline-none focus:ring-1 focus:ring-ring rounded px-1.5 py-1 leading-snug"
      />

      <div className="flex items-center gap-2 flex-wrap">
        <Select value={c.kind} onValueChange={(v) => onPatch({ kind: v as FactKind })}>
          <SelectTrigger className="h-7 text-xs w-[150px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {KIND_OPTIONS.map(k => (
              <SelectItem key={k} value={k}>{KIND_LABEL[k]}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={c.tier} onValueChange={(v) => onPatch({ tier: v as FactTier })}>
          <SelectTrigger className="h-7 text-xs w-[110px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TIER_OPTIONS.map(t => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex items-center gap-1.5">
          <Label className="text-[11px] text-muted-foreground">imp</Label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={c.importance}
            onChange={(e) => onPatch({ importance: parseFloat(e.target.value) })}
            className="w-20 accent-primary"
          />
          <span className="text-[11px] text-muted-foreground w-7 text-right">
            {c.importance.toFixed(2)}
          </span>
        </div>

        {!c.verified && (
          <Badge
            variant="outline"
            className="text-[11px] text-amber-700 border-amber-300 bg-amber-50"
            title={(c.verification_failures || []).join(' · ') || 'failed verifier'}
          >
            <AlertTriangle className="size-3 mr-1" /> low confidence
          </Badge>
        )}

        <div className="ml-auto flex items-center gap-1">
          {c._error && (
            <span className="text-[11px] text-destructive">{c._error}</span>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
            onClick={onRemove}
            title="Discard candidate"
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      </div>
    </div>
  )
}
