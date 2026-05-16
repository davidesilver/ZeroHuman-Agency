'use client'

import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Settings as SettingsIcon, Bot, Mail, Clock,
  Building, Plus, Loader2, ExternalLink, Brain, ImageIcon, Link2,
  Server, Bell, Search,
} from 'lucide-react'
import { useBrand } from '@/lib/brand-context'
import Link from 'next/link'

// ── Types ─────────────────────────────────────────────────────────────────────
// Shape returned by GET /api/system/config
interface SystemConfig {
  api_keys: {
    anthropic: boolean
    openrouter: boolean
    serper: boolean
    youtube: boolean
    resend: boolean
    firecrawl: boolean
  }
  image_backends: {
    default_backend: string
    default_model: string
    replicate: boolean
    openai: boolean
    pillo: boolean
    openrouter: boolean
    anthropic: boolean
  }
  postiz: {
    mode: string             // disabled | self_hosted | cloud
    api_url: string
    api_key: boolean
  }
  alerts: {
    telegram_bot: boolean
    telegram_chat: boolean
  }
  operations: {
    scheduler_secret: boolean
    python_backend_url: string
    allowed_origins: string
    scheduler_brand_id: string
  }
  llm: {
    scoring_model: string
    auto_approve_score: number
    auto_reject_score: number
  }
  email: {
    from_email: string
    from_name: string
  }
  research: {
    dedup_threshold: number
    max_items_retriever: number
  }
  scheduler: {
    daily_pipeline: string
    feedback_loop: string
    publish_scheduled: string
  }
  budget: {
    daily_cap_usd: number | null
  }
  social: {
    linkedin: boolean
    twitter: boolean
    instagram: boolean
    tiktok: boolean
  }
}

// Shape returned by GET /api/system/llm-routing
interface ModelRef {
  model_id: string
  provider: string
  cost_tier: string
}
interface CapabilityRoute {
  key: string
  label: string
  primary: ModelRef | null
  fallbacks: ModelRef[]
}
interface LLMRouting {
  backend_online: boolean
  capabilities: CapabilityRoute[]
  emergency_fallbacks: ModelRef[]
}

// ── Reusable building blocks ──────────────────────────────────────────────────

function StatusBadge({ configured, label }: { configured: boolean | null; label?: string }) {
  if (configured === null) {
    return <Badge variant="outline" className="text-[10px] text-muted-foreground">Loading…</Badge>
  }
  if (configured) {
    return <Badge className="text-[10px] bg-green-600 hover:bg-green-600">{label || 'Configured'}</Badge>
  }
  return <Badge variant="outline" className="text-[10px] text-amber-600 border-amber-600/40">Not set</Badge>
}

function PostizModeBadge({ mode }: { mode: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    disabled:    { label: 'Disabled',    cls: 'text-muted-foreground border-muted-foreground/40' },
    self_hosted: { label: 'Self-hosted', cls: 'bg-blue-600 text-white border-blue-600' },
    cloud:       { label: 'Cloud',       cls: 'bg-indigo-600 text-white border-indigo-600' },
  }
  const m = map[mode] ?? map.disabled
  return <Badge variant="outline" className={`text-[10px] ${m.cls}`}>{m.label}</Badge>
}

function Row({ label, envKey, hint, children }: {
  label: string
  envKey?: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5 border-b border-border last:border-0">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-sm whitespace-nowrap">{label}</span>
        {envKey && (
          <code className="text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded shrink-0">
            {envKey}
          </code>
        )}
        {hint && <span className="text-[11px] text-muted-foreground truncate">{hint}</span>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}

function MonoValue({ value, fallback = '…', placeholder }: {
  value: string | number | null | undefined
  fallback?: string
  placeholder?: string
}) {
  if (value == null || value === '') {
    if (placeholder) return <span className="text-sm text-amber-600">{placeholder}</span>
    return <span className="animate-pulse text-sm text-muted-foreground">{fallback}</span>
  }
  return <span className="text-sm font-mono text-muted-foreground">{value}</span>
}

// ── Health Overview (shown at top) ────────────────────────────────────────────

function HealthOverview({ cfg }: { cfg: SystemConfig | null }) {
  const stats = useMemo(() => {
    if (!cfg) return null
    const llm = (cfg.api_keys.anthropic ? 1 : 0) + (cfg.api_keys.openrouter ? 1 : 0)
    const research =
      (cfg.api_keys.serper ? 1 : 0) +
      (cfg.api_keys.youtube ? 1 : 0) +
      (cfg.api_keys.firecrawl ? 1 : 0)
    const imageBackends =
      (cfg.image_backends.replicate ? 1 : 0) +
      (cfg.image_backends.openai ? 1 : 0) +
      (cfg.image_backends.pillo ? 1 : 0) +
      (cfg.image_backends.openrouter ? 1 : 0) +
      (cfg.image_backends.anthropic ? 1 : 0)
    const postizConfigured = cfg.postiz.mode !== 'disabled' && cfg.postiz.api_key
    return {
      llmReady: llm > 0,
      llmCount: llm,
      researchCount: research,
      imageReady: imageBackends > 0 || cfg.image_backends.default_backend === 'mock',
      imageCount: imageBackends,
      newsletterReady: cfg.api_keys.resend && !!cfg.email.from_email,
      socialReady: postizConfigured,
      postizMode: cfg.postiz.mode,
      schedulerReady: cfg.operations.scheduler_secret,
      backendUrlSet: !!cfg.operations.python_backend_url,
    }
  }, [cfg])

  if (!cfg || !stats) {
    return (
      <Card>
        <CardContent className="py-4">
          <div className="animate-pulse text-sm text-muted-foreground">Loading system status…</div>
        </CardContent>
      </Card>
    )
  }

  const tile = (ok: boolean, label: string, sub: string) => (
    <div className={`rounded-md border px-3 py-2 ${
      ok ? 'border-green-600/30 bg-green-600/5' : 'border-amber-600/30 bg-amber-600/5'
    }`}>
      <div className="flex items-center gap-1.5">
        <span className={`size-1.5 rounded-full ${ok ? 'bg-green-600' : 'bg-amber-500'}`} />
        <span className="text-xs font-medium">{label}</span>
      </div>
      <div className="text-[11px] text-muted-foreground mt-0.5">{sub}</div>
    </div>
  )

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Server className="size-4 text-muted-foreground" />
          System Status
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
          {tile(stats.llmReady,        'LLM',        `${stats.llmCount}/2 providers`)}
          {tile(stats.researchCount > 0,'Research',  `${stats.researchCount}/3 sources`)}
          {tile(stats.imageReady,      'Images',     stats.imageCount > 0
                                                      ? `${stats.imageCount} backends`
                                                      : 'mock only')}
          {tile(stats.newsletterReady, 'Newsletter', stats.newsletterReady ? 'ready' : 'needs Resend + from')}
          {tile(stats.socialReady,     'Social',     stats.postizMode === 'disabled'
                                                      ? 'Postiz off'
                                                      : `Postiz ${stats.postizMode}`)}
          {tile(stats.schedulerReady && stats.backendUrlSet, 'Operations', stats.schedulerReady ? 'cron ready' : 'no SCHEDULER_SECRET')}
        </div>
      </CardContent>
    </Card>
  )
}

// ── LLM Routing Matrix ───────────────────────────────────────────────────────
// Shows the capability → primary/fallback model chain pulled from the Python
// backend (config/llm_models.py is the single source of truth).

function ProviderDot({ provider }: { provider: string }) {
  const map: Record<string, string> = {
    anthropic:  'bg-orange-500',
    openai:     'bg-emerald-500',
    openrouter: 'bg-violet-500',
    google:     'bg-sky-500',
  }
  const cls = map[provider] ?? 'bg-muted-foreground'
  return <span className={`size-1.5 rounded-full ${cls} shrink-0`} title={provider} />
}

function ModelChip({ model, kind = 'fallback' }: { model: ModelRef; kind?: 'primary' | 'fallback' }) {
  const isPrimary = kind === 'primary'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-[11px] font-mono ${
        isPrimary
          ? 'bg-green-600/10 text-green-700 dark:text-green-400 border border-green-600/30'
          : 'bg-secondary text-muted-foreground border border-border'
      }`}
      title={`${model.provider} · ${model.cost_tier}`}
    >
      <ProviderDot provider={model.provider} />
      {model.model_id}
    </span>
  )
}

// ── Provider Stats card (Phase 4) ───────────────────────────────────────────
interface ProviderStat {
  provider: string
  window: string
  total_calls: number
  error_rate: number
  avg_latency_ms: number | null
  total_cost_usd: number
  cost_per_1k_tokens: number | null
}

function OpenClawShareCard() {
  const { activeBrand } = useBrand()
  const [share, setShare] = useState(0)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!activeBrand) return
    fetch('/api/feature-flags?key=llm_provider_openclaw_share')
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.value != null) setShare(Math.round(parseFloat(d.value) * 100)) })
      .catch(() => {})
  }, [activeBrand])

  async function save() {
    if (!activeBrand) return
    setSaving(true)
    setSaved(false)
    try {
      await fetch('/api/feature-flags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          key: 'llm_provider_openclaw_share',
          value: share / 100,
          brand_id: activeBrand.id,
        }),
      })
      setSaved(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Bot className="size-4 text-muted-foreground" />
          OpenClaw A/B Split
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground">
          Route a percentage of LLM calls to OpenClaw for cost and latency comparison. Requires an OpenClaw API key in brand integrations.
        </p>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min={0}
            max={100}
            value={share}
            onChange={e => setShare(Number(e.target.value))}
            className="flex-1"
          />
          <span className="text-sm font-mono w-12 text-right">{share}%</span>
        </div>
        <div className="flex gap-2 items-center">
          <Button size="sm" onClick={save} disabled={saving || !activeBrand}>
            {saving ? <Loader2 className="size-3 animate-spin mr-1" /> : null}
            Save
          </Button>
          {saved && <span className="text-xs text-green-600">Saved</span>}
        </div>
      </CardContent>
    </Card>
  )
}

function ProviderStatsCard() {
  const [stats, setStats] = useState<ProviderStat[]>([])
  const [loading, setLoading] = useState(true)
  const [window, setWindow] = useState<'24h' | '7d' | '30d'>('7d')

  useEffect(() => {
    setLoading(true)
    fetch(`/api/llm/providers/metrics?window=${window}`)
      .then(r => r.ok ? r.json() : [])
      .then(setStats)
      .catch(() => setStats([]))
      .finally(() => setLoading(false))
  }, [window])

  if (!loading && stats.length === 0) return null

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Bot className="size-4 text-muted-foreground" />
            Provider Stats
          </CardTitle>
          <div className="flex gap-1">
            {(['24h', '7d', '30d'] as const).map(w => (
              <button
                key={w}
                onClick={() => setWindow(w)}
                className={`text-xs px-2 py-0.5 rounded ${
                  window === w ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {w}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" /> Loading...
          </div>
        ) : (
          <div className="space-y-2">
            {stats.map(s => (
              <div key={s.provider} className="text-xs grid grid-cols-4 gap-2 items-center">
                <span className="font-mono font-medium">{s.provider}</span>
                <span className="text-muted-foreground">{s.total_calls} calls</span>
                <span className="text-muted-foreground">
                  {s.avg_latency_ms != null ? `${s.avg_latency_ms}ms` : '—'}
                </span>
                <span className="text-muted-foreground">
                  {s.cost_per_1k_tokens != null
                    ? `$${s.cost_per_1k_tokens.toFixed(4)}/1k`
                    : `$${s.total_cost_usd.toFixed(4)}`}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function LLMRoutingMatrix({ routing }: { routing: LLMRouting | null }) {
  if (!routing) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="size-4 text-muted-foreground" />
            Agent Model Routing
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse text-sm text-muted-foreground">Loading routing matrix…</div>
        </CardContent>
      </Card>
    )
  }

  if (!routing.backend_online) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="size-4 text-muted-foreground" />
            Agent Model Routing
            <Badge variant="outline" className="text-[10px] text-amber-600 border-amber-600/40">
              Backend offline
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Could not reach the Python backend at <code className="bg-secondary px-1 rounded">PYTHON_BACKEND_URL</code>.
            Start it with <code className="bg-secondary px-1 rounded">make backend</code> to see the
            primary/fallback model chain used by each agent.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="size-4 text-muted-foreground" />
            Agent Model Routing
            <Badge variant="secondary" className="text-[10px] ml-1">
              {routing.capabilities.length} capabilities
            </Badge>
          </CardTitle>
          <code className="text-[10px] text-muted-foreground">
            python/config/llm_models.py
          </code>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2.5">
          {routing.capabilities.map(cap => (
            <div
              key={cap.key}
              className="grid grid-cols-[120px_1fr] gap-3 items-start py-1.5 border-b border-border last:border-0"
            >
              <div className="pt-0.5">
                <div className="text-sm font-medium capitalize">{cap.key.replace('_', ' ')}</div>
                <div className="text-[10px] text-muted-foreground">{cap.label}</div>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                {cap.primary && <ModelChip model={cap.primary} kind="primary" />}
                {cap.fallbacks.length > 0 && (
                  <>
                    <span className="text-[10px] text-muted-foreground mx-0.5">→</span>
                    {cap.fallbacks.map(m => (
                      <ModelChip key={m.model_id} model={m} kind="fallback" />
                    ))}
                  </>
                )}
              </div>
            </div>
          ))}

          {routing.emergency_fallbacks.length > 0 && (
            <div className="grid grid-cols-[120px_1fr] gap-3 items-start pt-3 mt-2 border-t border-dashed">
              <div className="pt-0.5">
                <div className="text-sm font-medium">Emergency</div>
                <div className="text-[10px] text-muted-foreground">free-tier last resort</div>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                {routing.emergency_fallbacks.map(m => (
                  <ModelChip key={m.model_id} model={m} />
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="mt-3 flex flex-wrap gap-3 text-[10px] text-muted-foreground">
          <span className="inline-flex items-center gap-1"><ProviderDot provider="anthropic" /> Anthropic</span>
          <span className="inline-flex items-center gap-1"><ProviderDot provider="openai" /> OpenAI</span>
          <span className="inline-flex items-center gap-1"><ProviderDot provider="openrouter" /> OpenRouter</span>
          <span className="ml-auto">
            Primary = green · order = priority. Models are tried left-to-right on failure.
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Add Brand card (unchanged logic, reads from useBrand) ────────────────────
function AddBrandCard() {
  const { brands, setActiveBrand } = useBrand()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [topics, setTopics] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleNameChange = (v: string) => {
    setName(v)
    setSlug(v.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, ''))
  }

  const handleCreate = async () => {
    if (!name.trim() || !slug.trim()) return
    setSaving(true)
    setError(null)
    try {
      const resp = await fetch('/api/brands', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          slug: slug.trim(),
          topics: topics ? topics.split(',').map(t => t.trim()).filter(Boolean) : [],
        }),
      })
      const json = await resp.json()
      if (json.success) {
        const newBrand = { id: json.data.id, name: json.data.name, slug: json.data.slug }
        setActiveBrand(newBrand)
        setName(''); setSlug(''); setTopics('')
        setOpen(false)
        window.location.reload()
      } else {
        setError(json.error?.message || 'Failed to create brand')
      }
    } catch {
      setError('Network error')
    }
    setSaving(false)
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Building className="size-4 text-muted-foreground" />
            Brands
            <Badge variant="secondary" className="text-[10px] ml-1">{brands.length}</Badge>
          </CardTitle>
          <div className="flex items-center gap-2">
            <Link
              href="/brands"
              className="inline-flex items-center gap-1 h-7 px-2.5 text-xs rounded-lg
                         hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
            >
              <ExternalLink className="size-3" /> Manage
            </Link>
            <Button
              size="sm"
              className="h-7 text-xs gap-1 bg-staging-bg hover:bg-staging-bg/90 text-white"
              onClick={() => { setOpen(!open); setError(null) }}
            >
              <Plus className="size-3" /> Add brand
            </Button>
          </div>
        </div>
      </CardHeader>
      {open && (
        <CardContent className="pt-0">
          <div className="space-y-3 p-3 bg-secondary/40 rounded-md">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Name</Label>
                <Input value={name} onChange={e => handleNameChange(e.target.value)} placeholder="My Brand" className="h-8 text-sm" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Slug <span className="text-muted-foreground">(auto)</span></Label>
                <Input value={slug} onChange={e => setSlug(e.target.value)} placeholder="my-brand" className="h-8 text-sm" />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Topics <span className="text-muted-foreground">(comma separated)</span></Label>
              <Input value={topics} onChange={e => setTopics(e.target.value)} placeholder="logistics, sustainability, B2B" className="h-8 text-sm" />
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setOpen(false)}>Cancel</Button>
              <Button
                size="sm"
                className="h-7 text-xs bg-staging-bg hover:bg-staging-bg/90 text-white"
                disabled={saving || !name.trim() || !slug.trim()}
                onClick={handleCreate}
              >
                {saving ? <Loader2 className="size-3 animate-spin" /> : null}
                {saving ? 'Creating…' : 'Create'}
              </Button>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function SettingsPage() {
  const [cfg, setCfg] = useState<SystemConfig | null>(null)
  const [routing, setRouting] = useState<LLMRouting | null>(null)

  useEffect(() => {
    fetch('/api/system/config')
      .then(r => r.json())
      .then(j => { if (j.success) setCfg(j.data) })
      .catch(() => {/* show loading state indefinitely on error */})

    // Routing matrix lives in Python (single source of truth in
    // config/llm_models.py); proxy returns backend_online=false on outage.
    fetch('/api/system/llm-routing')
      .then(r => r.json())
      .then(j => { if (j.success) setRouting(j.data) })
      .catch(() => setRouting({ backend_online: false, capabilities: [], emergency_fallbacks: [] }))
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Settings</h1>
        <Badge variant="outline" className="text-xs">
          <SettingsIcon className="size-3 mr-1" />
          Read-only (edit .env.local)
        </Badge>
      </div>

      {/* High-level system status */}
      <HealthOverview cfg={cfg} />

      {/* ── Tenancy ─────────────────────────────────────────────────────────── */}
      <AddBrandCard />

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Brain className="size-4 text-muted-foreground" />
              Brand Context Memory
            </CardTitle>
            <Link
              href="/settings/brand-context"
              className="inline-flex items-center gap-1 h-7 px-2.5 text-xs rounded-lg
                         hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
            >
              <ExternalLink className="size-3" /> Manage
            </Link>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <p className="text-xs text-muted-foreground">
            Tone rules, principles, gold examples and discard examples stored in semantic memory
            and automatically loaded by all AI agents.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <ImageIcon className="size-4 text-muted-foreground" />
              Brand Visual Assets
            </CardTitle>
            <Link
              href="/settings/brand-assets"
              className="inline-flex items-center gap-1 h-7 px-2.5 text-xs rounded-lg
                         hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
            >
              <ExternalLink className="size-3" /> Manage
            </Link>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <p className="text-xs text-muted-foreground">
            Logo, palette, design system, example newsletters and posts. Long-term editable assets
            referenced by the image generator and text agents.
          </p>
        </CardContent>
      </Card>

      {/* ── LLM Providers ───────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Bot className="size-4 text-muted-foreground" />
            LLM Providers
            <Badge variant="secondary" className="text-[10px] ml-1">at least one required</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Claude (Anthropic)" envKey="ANTHROPIC_API_KEY" hint="primary — Sonnet/Opus">
              <StatusBadge configured={cfg?.api_keys.anthropic ?? null} />
            </Row>
            <Row label="OpenRouter" envKey="OPENROUTER_API_KEY" hint="fallback or primary">
              <StatusBadge configured={cfg?.api_keys.openrouter ?? null} />
            </Row>
            <Row label="Scoring Model" envKey="SCORING_MODEL">
              <MonoValue value={cfg?.llm.scoring_model} />
            </Row>
            <Row label="Auto-approve threshold" envKey="AUTO_APPROVE_SCORE">
              <MonoValue value={cfg ? `≥ ${cfg.llm.auto_approve_score}` : null} />
            </Row>
            <Row label="Auto-reject threshold" envKey="AUTO_REJECT_SCORE">
              <MonoValue value={cfg ? `≤ ${cfg.llm.auto_reject_score}` : null} />
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* ── Agent Model Routing (primary + fallback chain per capability) ───── */}
      <LLMRoutingMatrix routing={routing} />

      {/* ── Provider Stats (Phase 4 telemetria) ─────────────────────────────── */}
      <ProviderStatsCard />

      {/* ── OpenClaw A/B Traffic Split (Phase 14) ────────────────────────────── */}
      <OpenClawShareCard />

      {/* ── Research APIs ───────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Search className="size-4 text-muted-foreground" />
            Research APIs
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Serper (Google search)" envKey="SERPER_API_KEY" hint="serper.dev">
              <StatusBadge configured={cfg?.api_keys.serper ?? null} />
            </Row>
            <Row label="YouTube Data API v3" envKey="YOUTUBE_API_KEY" hint="trend retriever">
              <StatusBadge configured={cfg?.api_keys.youtube ?? null} />
            </Row>
            <Row label="Firecrawl (premium scraping)" envKey="FIRECRAWL_API_KEY" hint="optional — falls back to trafilatura">
              <StatusBadge configured={cfg?.api_keys.firecrawl ?? null} label="Configured" />
            </Row>
            <Row label="Dedup similarity threshold" envKey="DEDUP_THRESHOLD">
              <MonoValue value={cfg?.research.dedup_threshold} />
            </Row>
            <Row label="Max items per retriever" envKey="MAX_ITEMS_PER_RETRIEVER">
              <MonoValue value={cfg?.research.max_items_retriever} />
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* ── Email / Newsletter ──────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Mail className="size-4 text-muted-foreground" />
            Email / Newsletter
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Resend API" envKey="RESEND_API_KEY" hint="resend.com">
              <StatusBadge configured={cfg?.api_keys.resend ?? null} />
            </Row>
            <Row label="From email" envKey="NEWSLETTER_FROM_EMAIL">
              <MonoValue value={cfg?.email.from_email} placeholder="not set" />
            </Row>
            <Row label="From name" envKey="NEWSLETTER_FROM_NAME">
              <MonoValue value={cfg?.email.from_name} />
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* ── Image Generation ────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <ImageIcon className="size-4 text-muted-foreground" />
              Image Generation
            </CardTitle>
            <Link
              href="/settings/image-generation"
              className="inline-flex items-center gap-1 h-7 px-2.5 text-xs rounded-lg
                         hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
            >
              <ExternalLink className="size-3" /> Per-brand config
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Default backend" envKey="DEFAULT_IMAGE_BACKEND">
              <MonoValue value={cfg?.image_backends.default_backend} />
            </Row>
            <Row label="Default model" envKey="DEFAULT_IMAGE_MODEL">
              <MonoValue value={cfg?.image_backends.default_model} />
            </Row>
            <Row label="Replicate" envKey="REPLICATE_API_TOKEN" hint="FLUX, SDXL">
              <StatusBadge configured={cfg?.image_backends.replicate ?? null} />
            </Row>
            <Row label="OpenAI" envKey="OPENAI_API_KEY" hint="DALL-E 3">
              <StatusBadge configured={cfg?.image_backends.openai ?? null} />
            </Row>
            <Row label="Pillo (carousel)" envKey="PILLO_API_KEY" hint="multi-slide specialist">
              <StatusBadge configured={cfg?.image_backends.pillo ?? null} />
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* ── Social Publishing (Postiz) ──────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Link2 className="size-4 text-muted-foreground" />
              Social Publishing (Postiz)
              {cfg && <PostizModeBadge mode={cfg.postiz.mode} />}
            </CardTitle>
            <Link
              href="/settings/social-connections"
              className="inline-flex items-center gap-1 h-7 px-2.5 text-xs rounded-lg
                         hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
            >
              <ExternalLink className="size-3" /> Connections
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Mode" envKey="POSTIZ_MODE" hint="disabled · self_hosted · cloud">
              <MonoValue value={cfg?.postiz.mode} />
            </Row>
            <Row label="API URL" envKey="POSTIZ_API_URL">
              <MonoValue value={cfg?.postiz.api_url} placeholder="not set" />
            </Row>
            <Row label="API Key" envKey="POSTIZ_API_KEY">
              <StatusBadge configured={cfg?.postiz.api_key ?? null} />
            </Row>
          </div>
          <p className="text-[11px] text-muted-foreground mt-2 leading-relaxed">
            OAuth and platform credentials live inside Postiz. Content Engine stores only the
            opaque integration IDs (managed in Connections).
          </p>
        </CardContent>
      </Card>

      {/* ── Email Marketing (Brevo) ──────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Mail className="size-4 text-muted-foreground" />
              Email Marketing (Brevo)
            </CardTitle>
            <Link
              href="/settings/audience"
              className="inline-flex items-center gap-1 h-7 px-2.5 text-xs rounded-lg
                         hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
            >
              <ExternalLink className="size-3" /> Audience
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            Connect Brevo for contact management, campaigns, and automations.
            Resend remains the default for transactional email.
          </p>
        </CardContent>
      </Card>

      {/* ── Cost Budget ─────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <span className="size-4 text-muted-foreground text-base leading-none">$</span>
            Cost Budget
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Global daily cap (all brands)" envKey="DAILY_COST_CAP_USD">
              <span className="text-sm font-mono text-muted-foreground">
                {!cfg
                  ? <span className="animate-pulse">…</span>
                  : cfg.budget.daily_cap_usd != null
                    ? `$${Number(cfg.budget.daily_cap_usd).toFixed(2)} / day`
                    : 'Unlimited'}
              </span>
            </Row>
            <Row label="Per-brand budget" envKey="">
              <Link
                href="/brands"
                className="inline-flex items-center gap-1 h-7 px-2.5 text-xs rounded-lg
                           hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
              >
                <ExternalLink className="size-3" /> Set per brand
              </Link>
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* ── Operations & Security ───────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Server className="size-4 text-muted-foreground" />
            Operations & Security
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Scheduler secret" envKey="SCHEDULER_SECRET" hint="protects cron endpoints">
              <StatusBadge configured={cfg?.operations.scheduler_secret ?? null} />
            </Row>
            <Row label="Python backend URL" envKey="PYTHON_BACKEND_URL">
              <MonoValue value={cfg?.operations.python_backend_url} placeholder="not set" />
            </Row>
            <Row label="Allowed origins (CORS)" envKey="ALLOWED_ORIGINS">
              <MonoValue value={cfg?.operations.allowed_origins} placeholder="not set" />
            </Row>
            <Row label="Scheduler brand ID" envKey="SCHEDULER_BRAND_ID" hint="empty = fan-out to all brands">
              <MonoValue value={cfg?.operations.scheduler_brand_id || 'fan-out'} />
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* ── Scheduler ───────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Clock className="size-4 text-muted-foreground" />
            Scheduler
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Daily research pipeline" envKey="CRON_DAILY_PIPELINE">
              <MonoValue value={cfg?.scheduler.daily_pipeline} />
            </Row>
            <Row label="Feedback loop update" envKey="CRON_FEEDBACK_LOOP">
              <MonoValue value={cfg?.scheduler.feedback_loop} />
            </Row>
            <Row label="Publish scheduled posts" envKey="CRON_PUBLISH_SCHEDULED">
              <MonoValue value={cfg?.scheduler.publish_scheduled} />
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* ── Alerts ──────────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Bell className="size-4 text-muted-foreground" />
            Alerts
            <Badge variant="secondary" className="text-[10px] ml-1">optional</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Telegram bot token" envKey="TELEGRAM_BOT_TOKEN" hint="@BotFather">
              <StatusBadge configured={cfg?.alerts.telegram_bot ?? null} />
            </Row>
            <Row label="Telegram chat ID" envKey="TELEGRAM_CHAT_ID" hint="@userinfobot">
              <StatusBadge configured={cfg?.alerts.telegram_chat ?? null} />
            </Row>
          </div>
          <p className="text-[11px] text-muted-foreground mt-2 leading-relaxed">
            When both are set, the backend sends pipeline error alerts and daily summaries via Telegram.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
