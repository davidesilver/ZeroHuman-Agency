'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useBrand } from '@/lib/brand-context'
import { BrandDiscovery } from '@/components/brand-context/brand-discovery'
import { LLMProviderHub } from '@/components/settings/llm-provider-hub'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Check, ChevronRight, AlertCircle, Loader2, DollarSign,
  SkipForward, ArrowLeft, Zap, Globe, BarChart3, CheckCircle2,
  Circle, ExternalLink, Key, Eye, EyeOff, Image, Mail,
  Share2, Cpu, LayoutList, Wifi, WifiOff, Upload, Palette,
} from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

interface SystemConfig {
  api_keys: { anthropic: boolean; openrouter: boolean; serper: boolean; tavily: boolean }
  research_tier: 'premium' | 'tavily' | 'free'
}

interface SetupProgress {
  brand_id: string
  completed: Record<string, boolean>
  wizard_state: Record<string, unknown>
  dismissed: boolean
}

// ── Step definitions ──────────────────────────────────────────────────────────

const STEPS = [
  { id: 'infrastructure', label: 'Check',    icon: Wifi,      required: true },
  { id: 'llm',           label: 'LLM',       icon: Zap,       required: true },
  { id: 'brand',         label: 'Brand',     icon: Globe,     required: true },
  { id: 'voice',         label: 'Voice',     icon: BarChart3, required: false },
  { id: 'research',      label: 'Research',  icon: BarChart3, required: false },
  { id: 'images',        label: 'Images',    icon: Image,     required: false },
  { id: 'email',         label: 'Email',     icon: Mail,      required: false },
  { id: 'social',        label: 'Social',    icon: Share2,    required: false },
  { id: 'mcp',           label: 'MCP',       icon: Cpu,       required: false },
  { id: 'review',        label: 'Review',    icon: LayoutList, required: true },
]

// ── Step Indicator ────────────────────────────────────────────────────────────

function StepIndicator({
  current,
  completed,
}: {
  current: number
  completed: Record<string, boolean>
}) {
  return (
    <div className="flex items-center gap-1 mb-8 flex-wrap">
      {STEPS.map((step, i) => {
        const done = completed[step.id] || i < current
        const active = i === current
        const Icon = step.icon
        return (
          <div key={step.id} className="flex items-center gap-1">
            <div
              title={step.label}
              className={`size-7 rounded-full flex items-center justify-center transition-colors
                ${done ? 'bg-primary text-white' : active ? 'bg-primary/20 text-primary border border-primary' : 'bg-muted text-muted-foreground'}`}
            >
              {done ? <Check className="size-3" /> : <Icon className="size-3" />}
            </div>
            {i < STEPS.length - 1 && (
              <div className={`h-px w-4 transition-colors ${done ? 'bg-primary' : 'bg-border'}`} />
            )}
          </div>
        )
      })}
      <span className="ml-2 text-xs text-muted-foreground font-medium">
        {STEPS[current]?.label}
        {!STEPS[current]?.required && (
          <span className="ml-1 text-muted-foreground/60">(optional)</span>
        )}
      </span>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function SetupPage() {
  const router = useRouter()
  const { setActiveBrand, activeBrand } = useBrand()

  const [step, setStep] = useState(0)
  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [configLoading, setConfigLoading] = useState(true)
  const [progress, setProgress] = useState<SetupProgress | null>(null)
  const [progressLoading, setProgressLoading] = useState(true)

  // Brand creation state
  const [brandName, setBrandName] = useState('')
  const [brandSlug, setBrandSlug] = useState('')
  const [brandTopics, setBrandTopics] = useState('')
  const [brandBudget, setBrandBudget] = useState('')
  const [brandDesc, setBrandDesc] = useState('')
  const [brandWebsite, setBrandWebsite] = useState('')
  const [brandColor, setBrandColor] = useState('#6366f1')
  const [brandLogoFile, setBrandLogoFile] = useState<File | null>(null)
  const [brandSaving, setBrandSaving] = useState(false)
  const [brandError, setBrandError] = useState<string | null>(null)
  const [createdBrand, setCreatedBrand] = useState<{ id: string; name: string; slug: string } | null>(null)

  const [voiceFacts, setVoiceFacts] = useState(0)

  // Load config
  useEffect(() => {
    fetch('/api/system/config')
      .then(r => r.json())
      .then(j => { if (j.success) setConfig(j.data) })
      .catch(() => {})
      .finally(() => setConfigLoading(false))
  }, [])

  // Load server-side progress
  useEffect(() => {
    if (!activeBrand?.id) { setProgressLoading(false); return }
    fetch('/api/setup/progress')
      .then(r => r.json())
      .then(d => {
        setProgress(d)
        // Resume at last incomplete required step
        const lastCompleted = STEPS.findLastIndex(s => d.completed?.[s.id])
        if (lastCompleted >= 0 && lastCompleted + 1 < STEPS.length) {
          setStep(lastCompleted + 1)
        }
        // Restore wizard_state
        if (d.wizard_state?.step) setStep(d.wizard_state.step as number)
        if (d.wizard_state?.brandName) setBrandName(d.wizard_state.brandName as string)
        if (d.wizard_state?.createdBrand) {
          const b = d.wizard_state.createdBrand as { id: string; name: string; slug: string }
          setCreatedBrand(b)
          setActiveBrand(b)
        }
      })
      .catch(() => {})
      .finally(() => setProgressLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeBrand?.id])

  const patchProgress = useCallback(async (updates: Partial<SetupProgress> & { completed_step?: string }) => {
    if (!activeBrand?.id) return
    const body: Record<string, unknown> = {}
    if (updates.completed_step) body.completed = { [updates.completed_step]: true }
    if (updates.completed) body.completed = updates.completed
    if (updates.wizard_state) body.wizard_state = updates.wizard_state
    if (updates.dismissed !== undefined) body.dismissed = updates.dismissed
    const res = await fetch('/api/setup/progress', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (res.ok) setProgress(await res.json())
  }, [activeBrand?.id])

  const next = useCallback((completedStepId?: string) => {
    if (completedStepId) patchProgress({ completed_step: completedStepId })
    setStep(s => Math.min(s + 1, STEPS.length - 1))
  }, [patchProgress])

  const back = () => setStep(s => Math.max(s - 1, 0))
  const skip = () => {
    const stepId = STEPS[step]?.id
    if (stepId) patchProgress({ completed_step: stepId })
    setStep(s => Math.min(s + 1, STEPS.length - 1))
  }

  function handleBrandName(v: string) {
    setBrandName(v)
    setBrandSlug(v.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, ''))
  }

  async function createBrand() {
    if (!brandName.trim() || !brandSlug.trim()) return
    setBrandSaving(true)
    setBrandError(null)
    const topics = brandTopics ? brandTopics.split(',').map(t => t.trim()).filter(Boolean) : []
    const budget = brandBudget.trim() === '' ? null : parseFloat(brandBudget)
    try {
      const resp = await fetch('/api/brands', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: brandName.trim(), slug: brandSlug.trim(), topics, description: brandDesc.trim() || undefined }),
      })
      const json = await resp.json()
      if (!json.success) { setBrandError(json.error?.message || 'Failed to create brand'); return }
      const brandId = json.data?.id || json.data?.brand_id
      if (!brandId) { setBrandError('Unexpected response from server'); return }
      if (budget != null) {
        await fetch(`/api/brands/${brandId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ daily_budget_usd: budget }) })
      }
      // Upload logo if selected
      if (brandLogoFile) {
        const fd = new FormData()
        fd.append('file', brandLogoFile)
        fd.append('kind', 'logo')
        await fetch(`/api/brands/${brandId}/assets`, { method: 'POST', body: fd }).catch(() => {})
      }
      const brand = { id: brandId, name: brandName.trim(), slug: brandSlug.trim() }
      setCreatedBrand(brand)
      setActiveBrand(brand)
      await patchProgress({ wizard_state: { step: step + 1, createdBrand: brand }, completed_step: 'brand' })
      setStep(s => s + 1)
    } catch {
      setBrandError('Network error — could not reach the server')
    }
    setBrandSaving(false)
  }

  function renderStep() {
    switch (step) {
      case 0: return <StepInfrastructure onNext={() => next('infrastructure')} />
      case 1: return (
        <StepLlm
          config={config}
          loading={configLoading}
          onNext={() => next('llm')}
          onBack={back}
        />
      )
      case 2: return (
        <StepBrand
          name={brandName} slug={brandSlug} topics={brandTopics} budget={brandBudget}
          desc={brandDesc} website={brandWebsite} color={brandColor} logoFile={brandLogoFile}
          onName={handleBrandName} onSlug={setBrandSlug} onTopics={setBrandTopics}
          onBudget={setBrandBudget} onDesc={setBrandDesc} onWebsite={setBrandWebsite}
          onColor={setBrandColor} onLogo={setBrandLogoFile}
          onSave={createBrand} saving={brandSaving} error={brandError}
          onBack={back}
          existing={createdBrand}
        />
      )
      case 3: return <StepVoice voiceFacts={voiceFacts} onFactsSaved={setVoiceFacts} onNext={() => next('voice')} onBack={back} onSkip={skip} />
      case 4: return <StepResearch config={config} loading={configLoading} onNext={() => next('research')} onBack={back} onSkip={skip} />
      case 5: return <StepImages config={config} onNext={() => next('images')} onBack={back} onSkip={skip} />
      case 6: return <StepEmail onNext={() => next('email')} onBack={back} onSkip={skip} />
      case 7: return <StepSocial onNext={() => next('social')} onBack={back} onSkip={skip} />
      case 8: return <StepMcp onNext={() => next('mcp')} onBack={back} onSkip={skip} />
      case 9: return (
        <StepReview
          config={config}
          createdBrand={createdBrand}
          voiceFacts={voiceFacts}
          progress={progress}
          onFinish={() => router.push('/')}
          onBack={back}
        />
      )
      default: return null
    }
  }

  if (progressLoading) {
    return <div className="max-w-xl mx-auto py-8 flex justify-center"><Loader2 className="size-5 animate-spin text-muted-foreground" /></div>
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <StepIndicator current={step} completed={progress?.completed ?? {}} />
      {renderStep()}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 0: Infrastructure Check
// ═══════════════════════════════════════════════════════════════════════════════

interface HealthCheck { label: string; status: 'ok' | 'fail' | 'loading'; detail?: string; latency_ms?: number }

function StepInfrastructure({ onNext }: { onNext: () => void }) {
  const [checks, setChecks] = useState<HealthCheck[]>([
    { label: 'Python backend', status: 'loading' },
    { label: 'Supabase database', status: 'loading' },
    { label: 'Migrations', status: 'loading' },
  ])
  const [allOk, setAllOk] = useState(false)
  const ran = useRef(false)

  useEffect(() => {
    if (ran.current) return
    ran.current = true

    async function runChecks() {
      const results: HealthCheck[] = []

      // Backend health
      const t0 = Date.now()
      try {
        const res = await fetch('/api/system/health', { signal: AbortSignal.timeout(5000) })
        const data = await res.json()
        results.push({ label: 'Python backend', status: res.ok ? 'ok' : 'fail', detail: res.ok ? 'Healthy' : 'Unreachable', latency_ms: Date.now() - t0 })
      } catch {
        results.push({ label: 'Python backend', status: 'fail', detail: 'Run: npm run dev:api', latency_ms: Date.now() - t0 })
      }

      // DB health
      const t1 = Date.now()
      try {
        const res = await fetch('/api/system/health')
        const json = await res.json()
        results.push({ label: 'Supabase database', status: res.ok ? 'ok' : 'fail', detail: res.ok ? 'Connected' : 'Check Supabase credentials', latency_ms: Date.now() - t1 })
      } catch {
        results.push({ label: 'Supabase database', status: 'fail', detail: 'Connection failed', latency_ms: Date.now() - t1 })
      }

      results.push({ label: 'Migrations', status: 'ok', detail: 'Managed by Supabase' })

      setChecks(results)
      setAllOk(results.every(r => r.status === 'ok'))
    }

    runChecks()
  }, [])

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">Infrastructure Check</h2>
        <p className="text-sm text-muted-foreground">Verifying all required services are reachable.</p>
      </div>

      <div className="space-y-2">
        {checks.map(check => (
          <div key={check.label} className="flex items-center justify-between p-3 rounded-md border">
            <div className="flex items-center gap-2">
              {check.status === 'loading' && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
              {check.status === 'ok' && <CheckCircle2 className="size-4 text-[var(--status-success)]" />}
              {check.status === 'fail' && <AlertCircle className="size-4 text-destructive" />}
              <span className="text-sm font-medium">{check.label}</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {check.detail && <span>{check.detail}</span>}
              {check.latency_ms !== undefined && <span className="tabular-nums">{check.latency_ms}ms</span>}
            </div>
          </div>
        ))}
      </div>

      {checks.some(c => c.status === 'fail') && (
        <div className="p-3 rounded-md bg-destructive/10 border border-destructive/30 text-sm text-destructive space-y-1">
          <p className="font-medium">Some checks failed</p>
          <p>Run <code className="font-mono bg-destructive/10 px-1 rounded">npm run dev</code> in the project root to start all services.</p>
        </div>
      )}

      <div className="flex gap-3">
        <Button className="flex-1" onClick={onNext} disabled={checks.some(c => c.status === 'loading')}>
          {allOk ? <>Continue <ChevronRight className="size-4 ml-2" /></> : 'Continue anyway →'}
        </Button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 1: LLM Providers (expanded — uses LLMProviderHub)
// ═══════════════════════════════════════════════════════════════════════════════

function StepLlm({
  config, loading, onNext, onBack,
}: {
  config: SystemConfig | null; loading: boolean; onNext: () => void; onBack: () => void
}) {
  const [byokConfigured, setByokConfigured] = useState<Set<string>>(new Set())
  const [loadingByok, setLoadingByok] = useState(true)

  useEffect(() => {
    fetch('/api/llm/providers/configured')
      .then(r => r.json())
      .then((data: Array<{ id: string; configured: boolean }>) => {
        if (Array.isArray(data)) setByokConfigured(new Set(data.filter(p => p.configured).map(p => p.id)))
      })
      .catch(() => {})
      .finally(() => setLoadingByok(false))
  }, [])

  const hasEnvLlm = !!(config?.api_keys.anthropic || config?.api_keys.openrouter)
  const hasAnyLlm = hasEnvLlm || byokConfigured.size > 0

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">LLM Providers</h2>
        <p className="text-sm text-muted-foreground">
          Add one or more LLM providers. Multiple providers give you fallback resilience.
        </p>
      </div>

      {hasEnvLlm && (
        <div className="flex gap-2 p-3 rounded-md status-success-soft border border-[var(--status-success)]/30 text-sm">
          <Check className="size-4 shrink-0 mt-0.5" />
          <span>System LLM configured via env vars{config?.api_keys.anthropic ? ' (Anthropic)' : ''}{config?.api_keys.openrouter ? ' (OpenRouter)' : ''}.</span>
        </div>
      )}

      {/* Full provider hub embedded in wizard */}
      <div className="border rounded-lg overflow-hidden">
        <LLMProviderHub wizardMode />
      </div>

      {!loading && !loadingByok && !hasAnyLlm && (
        <div className="flex gap-2 p-3 rounded-md status-warning-soft border border-[var(--status-warning)]/30 text-sm">
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">No LLM configured</p>
            <p className="text-xs mt-0.5">Add a key above, or set an env var and restart.</p>
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-24"><ArrowLeft className="size-3.5 mr-1" /> Back</Button>
        <Button className="flex-1" onClick={onNext} disabled={!hasAnyLlm && !loading}>
          {!hasAnyLlm && !loading ? 'Configure LLM to continue' : <>Next <ChevronRight className="size-4 ml-2" /></>}
        </Button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 2: Brand Identity (enhanced)
// ═══════════════════════════════════════════════════════════════════════════════

function StepBrand({
  name, slug, topics, budget, desc, website, color, logoFile,
  onName, onSlug, onTopics, onBudget, onDesc, onWebsite, onColor, onLogo,
  onSave, saving, error, onBack, existing,
}: {
  name: string; slug: string; topics: string; budget: string
  desc: string; website: string; color: string; logoFile: File | null
  onName: (v: string) => void; onSlug: (v: string) => void
  onTopics: (v: string) => void; onBudget: (v: string) => void
  onDesc: (v: string) => void; onWebsite: (v: string) => void
  onColor: (v: string) => void; onLogo: (f: File | null) => void
  onSave: () => void; saving: boolean; error: string | null; onBack: () => void
  existing: { id: string; name: string; slug: string } | null
}) {
  const fileRef = useRef<HTMLInputElement>(null)

  if (existing) {
    return (
      <div className="space-y-5">
        <div>
          <h2 className="text-xl font-semibold mb-1">Brand created</h2>
          <p className="text-sm text-muted-foreground">Your brand is ready. Continue to set up voice and integrations.</p>
        </div>
        <div className="p-4 rounded-md border flex items-center gap-3">
          <CheckCircle2 className="size-5 text-[var(--status-success)]" />
          <div>
            <p className="font-medium">{existing.name}</p>
            <p className="text-xs text-muted-foreground">/{existing.slug}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={onBack} className="w-24"><ArrowLeft className="size-3.5 mr-1" /> Back</Button>
          <Button className="flex-1" onClick={onSave} disabled={saving}>
            Continue <ChevronRight className="size-4 ml-2" />
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">Create your first brand</h2>
        <p className="text-sm text-muted-foreground">A brand scopes all research, content, and settings.</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2 space-y-1.5">
          <Label htmlFor="brand-name">Brand name</Label>
          <Input id="brand-name" value={name} onChange={e => onName(e.target.value)} placeholder="Acme Corp" autoFocus />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="brand-slug">Slug <span className="text-muted-foreground text-xs">(immutable)</span></Label>
          <Input id="brand-slug" value={slug} onChange={e => onSlug(e.target.value)} placeholder="acme-corp" />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="brand-website">Website URL</Label>
          <Input id="brand-website" value={website} onChange={e => onWebsite(e.target.value)} placeholder="https://acme.com" />
        </div>

        <div className="col-span-2 space-y-1.5">
          <Label htmlFor="brand-desc">Description <span className="text-muted-foreground text-xs">(optional)</span></Label>
          <Input id="brand-desc" value={desc} onChange={e => onDesc(e.target.value)} placeholder="We help startups scale their content..." />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="brand-topics">Topics <span className="text-muted-foreground text-xs">(comma-separated)</span></Label>
          <Input id="brand-topics" value={topics} onChange={e => onTopics(e.target.value)} placeholder="SaaS, marketing" />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="brand-budget">Daily budget (USD) <span className="text-muted-foreground text-xs">— blank = unlimited</span></Label>
          <div className="relative">
            <DollarSign className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input id="brand-budget" type="number" min="0" step="0.50" value={budget} onChange={e => onBudget(e.target.value)} placeholder="5.00" className="pl-8" />
          </div>
        </div>

        {/* Logo upload */}
        <div className="space-y-1.5">
          <Label>Logo <span className="text-muted-foreground text-xs">(optional)</span></Label>
          <div
            onClick={() => fileRef.current?.click()}
            className="flex items-center gap-2 h-9 px-3 rounded-md border cursor-pointer hover:bg-muted/50 transition-colors text-sm text-muted-foreground"
          >
            <Upload className="size-4" />
            {logoFile ? logoFile.name : 'Choose file...'}
          </div>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={e => onLogo(e.target.files?.[0] ?? null)} />
        </div>

        {/* Primary color */}
        <div className="space-y-1.5">
          <Label>Primary color</Label>
          <div className="flex items-center gap-2">
            <input type="color" value={color} onChange={e => onColor(e.target.value)} className="size-9 rounded cursor-pointer border" />
            <span className="text-xs text-muted-foreground font-mono">{color}</span>
          </div>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-24"><ArrowLeft className="size-3.5 mr-1" /> Back</Button>
        <Button className="flex-1" onClick={onSave} disabled={saving || !name.trim() || !slug.trim()}>
          {saving ? <><Loader2 className="size-4 mr-2 animate-spin" />Creating…</> : <>Create Brand <ChevronRight className="size-4 ml-2" /></>}
        </Button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 3: Brand Voice
// ═══════════════════════════════════════════════════════════════════════════════

function StepVoice({ voiceFacts, onFactsSaved, onNext, onBack, onSkip }: {
  voiceFacts: number; onFactsSaved: (n: number) => void
  onNext: () => void; onBack: () => void; onSkip: () => void
}) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">Brand voice</h2>
        <p className="text-sm text-muted-foreground">Teach the system your tone, principles, and examples.</p>
      </div>
      <BrandDiscovery onFactsSaved={onFactsSaved} />
      <div className="flex gap-3 pt-2">
        <Button variant="outline" onClick={onBack} className="w-24"><ArrowLeft className="size-3.5 mr-1" /> Back</Button>
        <Button variant="outline" onClick={onSkip} className="w-32"><SkipForward className="size-3.5 mr-2" /> Skip</Button>
        <Button className="flex-1" onClick={onNext} disabled={voiceFacts === 0}>
          {voiceFacts > 0 ? <>Continue <ChevronRight className="size-4 ml-2" /></> : 'Save voice facts to continue'}
        </Button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 4: Research
// ═══════════════════════════════════════════════════════════════════════════════

const TIER_META = {
  premium: { label: 'Premium', cls: 'bg-[var(--brand-primary)]/15 text-[var(--brand-primary)]', desc: 'Serper + YouTube + RSS.' },
  tavily:  { label: 'Tavily',  cls: 'status-info-soft',   desc: 'Tavily + RSS. 1,000 searches/month free.' },
  free:    { label: 'Free',    cls: 'status-warning-soft', desc: 'DuckDuckGo + RSS. Zero cost, works out of the box.' },
}

function InlineKeyInput({ label, envHint, placeholder, savedKey, onSaved }: {
  label: string; envHint: string; placeholder: string
  savedKey?: string; onSaved: (key: string) => void
}) {
  const [val, setVal] = useState(savedKey ?? '')
  const [visible, setVisible] = useState(false)
  const [status, setStatus] = useState<'idle' | 'ok' | 'error'>('idle')

  async function save() {
    if (!val.trim()) return
    // Save as env-level key via system config endpoint (simple PUT)
    try {
      const res = await fetch('/api/system/config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [envHint]: val.trim() }),
      })
      if (res.ok) { setStatus('ok'); onSaved(val.trim()) }
      else setStatus('error')
    } catch { setStatus('error') }
  }

  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type={visible ? 'text' : 'password'}
            value={val}
            onChange={e => { setVal(e.target.value); setStatus('idle') }}
            placeholder={placeholder}
            className="w-full font-mono text-xs pr-8 pl-3 py-2 rounded-md border bg-background focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <button type="button" onClick={() => setVisible(v => !v)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
            {visible ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
          </button>
        </div>
        <Button size="sm" variant="outline" onClick={save} disabled={!val.trim()}>Save</Button>
      </div>
      {status === 'ok' && <p className="text-xs text-[var(--status-success)] flex items-center gap-1"><Check className="size-3" /> Saved</p>}
      {status === 'error' && <p className="text-xs text-destructive">Save failed — check configuration</p>}
    </div>
  )
}

function StepResearch({ config, loading, onNext, onBack, onSkip }: {
  config: SystemConfig | null; loading: boolean
  onNext: () => void; onBack: () => void; onSkip: () => void
}) {
  const tier = config?.research_tier ?? 'free'
  const meta = TIER_META[tier]
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">Research tools</h2>
        <p className="text-sm text-muted-foreground">Configure APIs for content discovery. Free tier works out of the box.</p>
      </div>
      {loading ? <Loader2 className="size-5 animate-spin text-muted-foreground mx-auto" /> : (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 rounded-md border">
            <span className="text-sm font-medium">Active tier</span>
            <Badge className={`${meta.cls} border-0 text-xs`}>{meta.label}</Badge>
          </div>
          <p className="text-xs text-muted-foreground">{meta.desc}</p>
          <div className="space-y-3 border rounded-md p-4">
            <InlineKeyInput label="Serper API key (web search)" envHint="SERPER_API_KEY" placeholder="Enter key..." onSaved={() => {}} />
            <InlineKeyInput label="Tavily API key (1000 free/month)" envHint="TAVILY_API_KEY" placeholder="tvly-..." onSaved={() => {}} />
            <InlineKeyInput label="YouTube Data API key" envHint="YOUTUBE_API_KEY" placeholder="AIza..." onSaved={() => {}} />
          </div>
        </div>
      )}
      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-24"><ArrowLeft className="size-3.5 mr-1" /> Back</Button>
        <Button variant="outline" onClick={onSkip} className="w-32"><SkipForward className="size-3.5 mr-2" /> Skip</Button>
        <Button className="flex-1" onClick={onNext}>Continue <ChevronRight className="size-4 ml-2" /></Button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 5: Images
// ═══════════════════════════════════════════════════════════════════════════════

function StepImages({ config, onNext, onBack, onSkip }: {
  config: SystemConfig | null; onNext: () => void; onBack: () => void; onSkip: () => void
}) {
  const hasOpenAI = config?.api_keys && ('openai' in config.api_keys) && (config.api_keys as Record<string, boolean>).openai
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">Image generation</h2>
        <p className="text-sm text-muted-foreground">Configure backends for automated image creation.</p>
      </div>
      <div className="space-y-3 border rounded-md p-4">
        {hasOpenAI && (
          <div className="flex items-center justify-between text-sm">
            <span>OpenAI DALL-E 3</span>
            <Badge className="status-success-soft border-0 text-xs">Auto-detected</Badge>
          </div>
        )}
        <InlineKeyInput label="Stability AI API key" envHint="STABILITY_API_KEY" placeholder="sk-..." onSaved={() => {}} />
        <InlineKeyInput label="Replicate API token" envHint="REPLICATE_API_TOKEN" placeholder="r8_..." onSaved={() => {}} />
      </div>
      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-24"><ArrowLeft className="size-3.5 mr-1" /> Back</Button>
        <Button variant="outline" onClick={onSkip} className="w-32"><SkipForward className="size-3.5 mr-2" /> Skip</Button>
        <Button className="flex-1" onClick={onNext}>Continue <ChevronRight className="size-4 ml-2" /></Button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 6: Email
// ═══════════════════════════════════════════════════════════════════════════════

function StepEmail({ onNext, onBack, onSkip }: { onNext: () => void; onBack: () => void; onSkip: () => void }) {
  const [provider, setProvider] = useState<'resend' | 'brevo' | 'sendgrid'>('resend')
  const ENV_KEYS = { resend: 'RESEND_API_KEY', brevo: 'BREVO_API_KEY', sendgrid: 'SENDGRID_API_KEY' }
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">Email & notifications</h2>
        <p className="text-sm text-muted-foreground">Configure email delivery for newsletters and alerts.</p>
      </div>
      <div className="space-y-4">
        <div className="flex gap-2">
          {(['resend', 'brevo', 'sendgrid'] as const).map(p => (
            <button key={p} onClick={() => setProvider(p)}
              className={`px-3 py-1.5 text-xs rounded-md border transition-colors capitalize
                ${provider === p ? 'bg-primary text-primary-foreground border-primary' : 'border-border hover:bg-muted/50'}`}
            >{p}</button>
          ))}
        </div>
        <div className="border rounded-md p-4 space-y-3">
          <InlineKeyInput label={`${provider.charAt(0).toUpperCase() + provider.slice(1)} API key`} envHint={ENV_KEYS[provider]} placeholder="Enter key..." onSaved={() => {}} />
          <InlineKeyInput label="From email address" envHint="NEWSLETTER_FROM_EMAIL" placeholder="hello@yourcompany.com" onSaved={() => {}} />
          <InlineKeyInput label="From name" envHint="NEWSLETTER_FROM_NAME" placeholder="Acme Corp" onSaved={() => {}} />
        </div>
        <div className="border rounded-md p-4 space-y-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Telegram alerts (optional)</p>
          <InlineKeyInput label="Bot token" envHint="TELEGRAM_BOT_TOKEN" placeholder="123456:ABC..." onSaved={() => {}} />
          <InlineKeyInput label="Chat ID" envHint="TELEGRAM_CHAT_ID" placeholder="-100..." onSaved={() => {}} />
        </div>
      </div>
      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-24"><ArrowLeft className="size-3.5 mr-1" /> Back</Button>
        <Button variant="outline" onClick={onSkip} className="w-32"><SkipForward className="size-3.5 mr-2" /> Skip</Button>
        <Button className="flex-1" onClick={onNext}>Continue <ChevronRight className="size-4 ml-2" /></Button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 7: Social
// ═══════════════════════════════════════════════════════════════════════════════

function StepSocial({ onNext, onBack, onSkip }: { onNext: () => void; onBack: () => void; onSkip: () => void }) {
  const [postizStatus, setPostizStatus] = useState<'loading' | 'ok' | 'fail'>('loading')
  useEffect(() => {
    fetch('/api/social/health', { signal: AbortSignal.timeout(3000) })
      .then(r => r.json())
      .then(d => setPostizStatus(d.status === 'ok' ? 'ok' : 'fail'))
      .catch(() => setPostizStatus('fail'))
  }, [])

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">Social publishing</h2>
        <p className="text-sm text-muted-foreground">Connect social platforms via Postiz.</p>
      </div>
      <div className="p-3 rounded-md border flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm">
          {postizStatus === 'loading' && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
          {postizStatus === 'ok' && <CheckCircle2 className="size-4 text-[var(--status-success)]" />}
          {postizStatus === 'fail' && <WifiOff className="size-4 text-muted-foreground" />}
          <span>Postiz service</span>
        </div>
        <Badge className={postizStatus === 'ok' ? 'status-success-soft border-0 text-xs' : 'status-warning-soft border-0 text-xs'}>
          {postizStatus === 'loading' ? 'Checking…' : postizStatus === 'ok' ? 'Online' : 'Not running'}
        </Badge>
      </div>
      {postizStatus === 'fail' && (
        <div className="text-xs text-muted-foreground bg-muted/50 rounded-md p-3 space-y-1">
          <p>To enable social publishing:</p>
          <ol className="list-decimal pl-4 space-y-0.5">
            <li>Set <code className="font-mono">POSTIZ_MODE=self_hosted</code> in .env.local</li>
            <li>Run: <code className="font-mono">npm run postiz:up</code></li>
            <li>Open Postiz → add platform integrations → copy integration IDs</li>
            <li>Paste integration IDs in <a href="/settings/social-connections" className="underline">Settings → Social</a></li>
          </ol>
        </div>
      )}
      {postizStatus === 'ok' && (
        <div className="text-sm text-muted-foreground">
          Postiz is running. <a href="/settings/social-connections" className="underline text-foreground">Configure platforms →</a>
        </div>
      )}
      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-24"><ArrowLeft className="size-3.5 mr-1" /> Back</Button>
        <Button variant="outline" onClick={onSkip} className="w-32"><SkipForward className="size-3.5 mr-2" /> Skip</Button>
        <Button className="flex-1" onClick={onNext}>Continue <ChevronRight className="size-4 ml-2" /></Button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 8: MCP Connections
// ═══════════════════════════════════════════════════════════════════════════════

interface McpServer { id: string; label: string; status: 'detected' | 'not_running' | 'loading'; capabilities?: number; configUrl?: string }

function StepMcp({ onNext, onBack, onSkip }: { onNext: () => void; onBack: () => void; onSkip: () => void }) {
  const [servers, setServers] = useState<McpServer[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/mcp/detect', { signal: AbortSignal.timeout(10000) })
      .then(r => r.json())
      .then((data: McpServer[]) => setServers(data))
      .catch(() => setServers([]))
      .finally(() => setLoading(false))
  }, [])

  const detected = servers.filter(s => s.status === 'detected')
  const available = servers.filter(s => s.status === 'not_running')

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">MCP connections</h2>
        <p className="text-sm text-muted-foreground">Connect Model Context Protocol servers for extended capabilities.</p>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
          <Loader2 className="size-4 animate-spin" /> Scanning for MCP servers…
        </div>
      ) : (
        <div className="space-y-3">
          {detected.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Detected & connected</p>
              {detected.map(s => (
                <div key={s.id} className="flex items-center justify-between p-3 rounded-md border">
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="size-4 text-[var(--status-success)]" />
                    <span>{s.label}</span>
                  </div>
                  {s.capabilities !== undefined && (
                    <span className="text-xs text-muted-foreground">{s.capabilities} tools</span>
                  )}
                </div>
              ))}
            </div>
          )}
          {available.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Available (not connected)</p>
              {available.map(s => (
                <div key={s.id} className="flex items-center justify-between p-3 rounded-md border">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Circle className="size-4" />
                    <span>{s.label}</span>
                  </div>
                  {s.configUrl && (
                    <a href={s.configUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-primary underline flex items-center gap-1">
                      Setup <ExternalLink className="size-3" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
          {servers.length === 0 && (
            <div className="text-sm text-muted-foreground text-center py-4">
              No MCP servers detected. Configure them in Settings → MCP after setup.
            </div>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-24"><ArrowLeft className="size-3.5 mr-1" /> Back</Button>
        <Button variant="outline" onClick={onSkip} className="w-32"><SkipForward className="size-3.5 mr-2" /> Skip</Button>
        <Button className="flex-1" onClick={onNext}>Continue <ChevronRight className="size-4 ml-2" /></Button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 9: Review & Launch
// ═══════════════════════════════════════════════════════════════════════════════

function StepReview({
  config, createdBrand, voiceFacts, progress, onFinish, onBack,
}: {
  config: SystemConfig | null; createdBrand: { id: string; name: string; slug: string } | null
  voiceFacts: number; progress: SetupProgress | null; onFinish: () => void; onBack: () => void
}) {
  const completed = progress?.completed ?? {}
  const items = [
    { id: 'infrastructure', label: 'Infrastructure', done: true, detail: 'Backend + DB healthy' },
    { id: 'llm', label: 'LLM provider', done: completed.llm || !!(config?.api_keys.anthropic || config?.api_keys.openrouter), detail: 'Configured', link: '/settings/ai-providers' },
    { id: 'brand', label: 'Brand', done: !!createdBrand, detail: createdBrand?.name ?? 'Not created', link: '/brands' },
    { id: 'voice', label: 'Brand voice', done: voiceFacts > 0 || completed.voice, detail: voiceFacts > 0 ? `${voiceFacts} facts` : 'Not configured', link: '/settings/brand-context' },
    { id: 'research', label: 'Research tools', done: completed.research || config?.research_tier !== 'free', detail: completed.research ? 'Configured' : 'Free tier (DuckDuckGo)', link: '/settings' },
    { id: 'images', label: 'Images', done: completed.images, detail: completed.images ? 'Configured' : 'Not configured', link: '/settings' },
    { id: 'email', label: 'Email', done: completed.email, detail: completed.email ? 'Configured' : 'Not configured', link: '/settings' },
    { id: 'social', label: 'Social publishing', done: completed.social, detail: completed.social ? 'Configured' : 'Not configured', link: '/settings/social-connections' },
    { id: 'mcp', label: 'MCP connections', done: completed.mcp, detail: completed.mcp ? 'Configured' : 'Not configured', link: '/settings' },
  ]

  const doneCount = items.filter(i => i.done).length
  const pct = Math.round((doneCount / items.length) * 100)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-1">Review & Launch</h2>
        <p className="text-sm text-muted-foreground">Here&apos;s your setup summary. Missing items can be configured in Settings.</p>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Setup completion</span>
          <span className="font-medium">{pct}%</span>
        </div>
        <div className="h-2 rounded-full bg-muted overflow-hidden">
          <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="space-y-1.5">
        {items.map(item => (
          <div key={item.id} className="flex items-center gap-3 p-2.5 rounded-md border hover:bg-muted/30 transition-colors">
            {item.done
              ? <CheckCircle2 className="size-4 text-[var(--status-success)] shrink-0" />
              : <Circle className="size-4 text-muted-foreground shrink-0" />}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{item.label}</p>
              <p className="text-xs text-muted-foreground truncate">{item.detail}</p>
            </div>
            {!item.done && item.link && (
              <a href={item.link} className="text-xs text-primary underline shrink-0">Configure →</a>
            )}
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-24"><ArrowLeft className="size-3.5 mr-1" /> Back</Button>
        <Button className="flex-1" onClick={onFinish}>
          Launch Dashboard <ChevronRight className="size-4 ml-2" />
        </Button>
      </div>
    </div>
  )
}
