'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Settings as SettingsIcon, Key, Bot, Mail, Share2, Database, Clock, Building, Plus, Loader2, ExternalLink, Brain } from 'lucide-react'
import { useBrand } from '@/lib/brand-context'
import Link from 'next/link'

// Shape returned by GET /api/system/config
interface SystemConfig {
  api_keys: {
    anthropic: boolean
    openrouter: boolean
    serper: boolean
    youtube: boolean
    resend: boolean
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
    daily_cap_usd: number
  }
  social: {
    linkedin: boolean
    twitter: boolean
    instagram: boolean
    tiktok: boolean
  }
}

function StatusBadge({ configured, label }: { configured: boolean | null; label?: string }) {
  if (configured === null) {
    return <Badge variant="outline" className="text-[10px] text-muted-foreground">Loading…</Badge>
  }
  if (configured) {
    return <Badge className="text-[10px] bg-green-600">{label || 'Configured'}</Badge>
  }
  return <Badge variant="outline" className="text-[10px] text-amber-600">Check .env.local</Badge>
}

function Row({ label, envKey, children }: { label: string; envKey?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
      <div className="flex items-center gap-2">
        <span className="text-sm">{label}</span>
        {envKey && (
          <code className="text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">
            {envKey}
          </code>
        )}
      </div>
      <div>{children}</div>
    </div>
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
                <Input value={name} onChange={e => handleNameChange(e.target.value)} placeholder="Silvestri Pallets" className="h-8 text-sm" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Slug <span className="text-muted-foreground">(auto)</span></Label>
                <Input value={slug} onChange={e => setSlug(e.target.value)} placeholder="silvestri-pallets" className="h-8 text-sm" />
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

  useEffect(() => {
    fetch('/api/system/config')
      .then(r => r.json())
      .then(j => { if (j.success) setCfg(j.data) })
      .catch(() => {/* show loading state indefinitely on error */})
  }, [])

  const k = cfg?.api_keys
  const llm = cfg?.llm
  const soc = cfg?.social
  const sch = cfg?.scheduler
  const res = cfg?.research
  const bud = cfg?.budget

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Settings</h1>
        <Badge variant="outline" className="text-xs">
          <SettingsIcon className="size-3 mr-1" />
          Read-only (edit .env.local)
        </Badge>
      </div>

      {/* Brands */}
      <AddBrandCard />

      {/* Brand Context Memory */}
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

      {/* API Keys */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Key className="size-4 text-muted-foreground" />
            API Keys
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Claude API" envKey="ANTHROPIC_API_KEY">
              <StatusBadge configured={k?.anthropic ?? null} />
            </Row>
            <Row label="OpenRouter" envKey="OPENROUTER_API_KEY">
              <StatusBadge configured={k?.openrouter ?? null} />
            </Row>
            <Row label="Serper (search)" envKey="SERPER_API_KEY">
              <StatusBadge configured={k?.serper ?? null} />
            </Row>
            <Row label="YouTube Data" envKey="YOUTUBE_API_KEY">
              <StatusBadge configured={k?.youtube ?? null} />
            </Row>
            <Row label="Resend (email)" envKey="RESEND_API_KEY">
              <StatusBadge configured={k?.resend ?? null} />
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* LLM Configuration */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Bot className="size-4 text-muted-foreground" />
            LLM Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Scoring Model" envKey="SCORING_MODEL">
              <span className="text-sm font-mono text-muted-foreground">
                {llm?.scoring_model ?? <span className="animate-pulse">…</span>}
              </span>
            </Row>
            <Row label="Auto-approve threshold" envKey="AUTO_APPROVE_SCORE">
              <span className="text-sm font-mono text-muted-foreground">
                {llm ? `≥ ${llm.auto_approve_score}` : <span className="animate-pulse">…</span>}
              </span>
            </Row>
            <Row label="Auto-reject threshold" envKey="AUTO_REJECT_SCORE">
              <span className="text-sm font-mono text-muted-foreground">
                {llm ? `≤ ${llm.auto_reject_score}` : <span className="animate-pulse">…</span>}
              </span>
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* Budget */}
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
                {bud ? `$${bud.daily_cap_usd.toFixed(2)} / day` : <span className="animate-pulse">…</span>}
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

      {/* Email / Newsletter */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Mail className="size-4 text-muted-foreground" />
            Email / Newsletter
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="From email" envKey="FROM_EMAIL">
              <span className="text-sm font-mono text-muted-foreground">
                {cfg ? (cfg.email.from_email || <em className="not-italic text-amber-600">not set</em>) : <span className="animate-pulse">…</span>}
              </span>
            </Row>
            <Row label="From name" envKey="FROM_NAME">
              <span className="text-sm font-mono text-muted-foreground">
                {cfg ? cfg.email.from_name : <span className="animate-pulse">…</span>}
              </span>
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* Social Platforms */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Share2 className="size-4 text-muted-foreground" />
            Social Platforms
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="LinkedIn" envKey="LINKEDIN_TOKEN">
              <StatusBadge configured={soc?.linkedin ?? null} label="Connected" />
            </Row>
            <Row label="Twitter/X" envKey="TWITTER_BEARER_TOKEN">
              <StatusBadge configured={soc?.twitter ?? null} label="Connected" />
            </Row>
            <Row label="Instagram" envKey="INSTAGRAM_TOKEN">
              <StatusBadge configured={soc?.instagram ?? null} label="Connected" />
            </Row>
            <Row label="TikTok" envKey="TIKTOK_TOKEN">
              <StatusBadge configured={soc?.tiktok ?? null} label="Connected" />
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* Research Pipeline */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Database className="size-4 text-muted-foreground" />
            Research Pipeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <Row label="Dedup similarity threshold" envKey="DEDUP_THRESHOLD">
              <span className="text-sm font-mono text-muted-foreground">
                {res ? res.dedup_threshold : <span className="animate-pulse">…</span>}
              </span>
            </Row>
            <Row label="Max items per retriever" envKey="MAX_ITEMS_PER_RETRIEVER">
              <span className="text-sm font-mono text-muted-foreground">
                {res ? res.max_items_retriever : <span className="animate-pulse">…</span>}
              </span>
            </Row>
          </div>
        </CardContent>
      </Card>

      {/* Scheduler */}
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
              <span className="text-sm font-mono text-muted-foreground">
                {sch ? sch.daily_pipeline : <span className="animate-pulse">…</span>}
              </span>
            </Row>
            <Row label="Feedback loop update" envKey="CRON_FEEDBACK_LOOP">
              <span className="text-sm font-mono text-muted-foreground">
                {sch ? sch.feedback_loop : <span className="animate-pulse">…</span>}
              </span>
            </Row>
            <Row label="Publish scheduled posts" envKey="CRON_PUBLISH_SCHEDULED">
              <span className="text-sm font-mono text-muted-foreground">
                {sch ? sch.publish_scheduled : <span className="animate-pulse">…</span>}
              </span>
            </Row>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
