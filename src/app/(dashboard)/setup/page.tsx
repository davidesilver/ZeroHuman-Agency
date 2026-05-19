'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useBrand } from '@/lib/brand-context'
import { BrandDiscovery } from '@/components/brand-context/brand-discovery'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Check, ChevronRight, AlertCircle, Loader2,
  DollarSign, SkipForward, ArrowLeft, Zap, Globe, BarChart3,
  CheckCircle2, Circle, ExternalLink,
} from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

interface SystemConfig {
  api_keys: { anthropic: boolean; openrouter: boolean; serper: boolean; tavily: boolean }
  research_tier: 'premium' | 'tavily' | 'free'
}

// ── Step indicator ─────────────────────────────────────────────────────────────

const STEP_LABELS = ['Welcome', 'LLM', 'Brand', 'Voice', 'Research', 'Done']

function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-1 mb-8">
      {Array.from({ length: total }).map((_, i) => {
        const done = i < current
        const active = i === current
        return (
          <div key={i} className="flex items-center gap-1">
            <div
              className={`size-6 rounded-full flex items-center justify-center text-[11px] font-semibold transition-colors
                ${done ? 'bg-primary text-white' : active ? 'bg-primary/20 text-primary border border-primary' : 'bg-muted text-muted-foreground'}`}
            >
              {done ? <Check className="size-3" /> : i + 1}
            </div>
            {i < total - 1 && (
              <div className={`h-px w-6 transition-colors ${i < current ? 'bg-primary' : 'bg-border'}`} />
            )}
          </div>
        )
      })}
      <span className="ml-3 text-xs text-muted-foreground font-medium">{STEP_LABELS[current]}</span>
    </div>
  )
}

// ── Persistence ───────────────────────────────────────────────────────────────

const WIZARD_KEY = 'setup_wizard_state'

interface WizardState {
  step: number
  brand: { id: string; name: string; slug: string } | null
}

function loadWizardState(): WizardState {
  if (typeof window === 'undefined') return { step: 0, brand: null }
  try {
    const raw = window.localStorage.getItem(WIZARD_KEY)
    if (!raw) return { step: 0, brand: null }
    return JSON.parse(raw) as WizardState
  } catch {
    return { step: 0, brand: null }
  }
}

function saveWizardState(state: WizardState) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(WIZARD_KEY, JSON.stringify(state))
}

function clearWizardState() {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(WIZARD_KEY)
}

// ── Main wizard ────────────────────────────────────────────────────────────────

export default function SetupPage() {
  const router = useRouter()
  const { setActiveBrand } = useBrand()

  const [step, setStep] = useState(0)
  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [configLoading, setConfigLoading] = useState(true)

  // Brand creation state
  const [brandName, setBrandName] = useState('')
  const [brandSlug, setBrandSlug] = useState('')
  const [brandTopics, setBrandTopics] = useState('')
  const [brandBudget, setBrandBudget] = useState('')
  const [brandSaving, setBrandSaving] = useState(false)
  const [brandError, setBrandError] = useState<string | null>(null)
  const [createdBrand, setCreatedBrand] = useState<{ id: string; name: string; slug: string } | null>(null)

  // Voice facts
  const [voiceFacts, setVoiceFacts] = useState(0)

  // Restore persisted state on mount
  useEffect(() => {
    const saved = loadWizardState()
    if (saved.step > 0) setStep(saved.step)
    if (saved.brand) {
      setCreatedBrand(saved.brand)
      setActiveBrand(saved.brand)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Persist whenever step or created brand changes
  useEffect(() => {
    saveWizardState({ step, brand: createdBrand })
  }, [step, createdBrand])

  useEffect(() => {
    fetch('/api/system/config')
      .then(r => r.json())
      .then(j => { if (j.success) setConfig(j.data) })
      .catch(() => {})
      .finally(() => setConfigLoading(false))
  }, [])

  const next = () => setStep(s => Math.min(s + 1, STEP_LABELS.length - 1))
  const back = () => setStep(s => Math.max(s - 1, 0))

  const hasLlm = !!(config?.api_keys.anthropic || config?.api_keys.openrouter)

  // ── Brand name → slug auto-fill ──────────────────────────────────────────────

  function handleBrandName(v: string) {
    setBrandName(v)
    setBrandSlug(v.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, ''))
  }

  // ── Brand creation ────────────────────────────────────────────────────────────

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
        body: JSON.stringify({ name: brandName.trim(), slug: brandSlug.trim(), topics }),
      })
      const json = await resp.json()
      if (!json.success) {
        setBrandError(json.error?.message || 'Failed to create brand')
        return
      }

      const brandId = json.data?.id || json.data?.brand_id
      if (!brandId) { setBrandError('Unexpected response from server'); return }

      if (budget != null) {
        await fetch(`/api/brands/${brandId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ daily_budget_usd: budget }),
        })
      }

      const brand = { id: brandId, name: brandName.trim(), slug: brandSlug.trim() }
      setCreatedBrand(brand)
      setActiveBrand(brand)
      next()
    } catch {
      setBrandError('Network error — could not reach the server')
    }
    setBrandSaving(false)
  }

  // ── Steps ─────────────────────────────────────────────────────────────────────

  function renderStep() {
    switch (step) {
      case 0: return <StepWelcome onNext={next} />
      case 1: return (
        <StepLlm
          config={config}
          loading={configLoading}
          hasLlm={hasLlm}
          onNext={next}
          onBack={back}
        />
      )
      case 2: return (
        <StepBrand
          name={brandName} slug={brandSlug} topics={brandTopics} budget={brandBudget}
          onName={handleBrandName}
          onSlug={setBrandSlug}
          onTopics={setBrandTopics}
          onBudget={setBrandBudget}
          onSave={createBrand}
          saving={brandSaving}
          error={brandError}
          onBack={back}
        />
      )
      case 3: return (
        <StepVoice
          voiceFacts={voiceFacts}
          onFactsSaved={setVoiceFacts}
          onNext={next}
          onBack={back}
        />
      )
      case 4: return (
        <StepResearch config={config} loading={configLoading} onNext={next} onBack={back} />
      )
      case 5: return (
        <StepDone
          config={config}
          createdBrand={createdBrand}
          voiceFacts={voiceFacts}
          onFinish={() => router.push('/')}
        />
      )
    }
  }

  return (
    <div className="max-w-xl mx-auto py-8">
      <StepIndicator current={step} total={STEP_LABELS.length} />
      {renderStep()}
    </div>
  )
}

// ── Step 0: Welcome ────────────────────────────────────────────────────────────

function StepWelcome({ onNext }: { onNext: () => void }) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-2">Welcome to ZeroHuman Agency</h1>
        <p className="text-muted-foreground">
          Your self-hosted AI content operations platform. Let's get your pipeline running in about 5 minutes.
        </p>
      </div>

      <div className="space-y-3">
        {[
          { icon: Zap, label: 'Verify your LLM provider is configured' },
          { icon: Globe, label: 'Create your first brand' },
          { icon: BarChart3, label: 'Set up your brand voice (optional)' },
          { icon: BarChart3, label: 'Review research configuration' },
        ].map(({ icon: Icon, label }, i) => (
          <div key={i} className="flex items-center gap-3 text-sm">
            <div className="size-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
              <Icon className="size-3.5 text-primary" />
            </div>
            <span>{label}</span>
          </div>
        ))}
      </div>

      <Button className="w-full" onClick={onNext}>
        Start Setup
        <ChevronRight className="size-4 ml-2" />
      </Button>

      <p className="text-center text-xs text-muted-foreground">
        Prefer to set up manually?{' '}
        <a href="/brands" className="underline underline-offset-2 hover:text-foreground">
          Skip wizard →
        </a>
      </p>
    </div>
  )
}

// ── Step 1: LLM ───────────────────────────────────────────────────────────────

function StepLlm({
  config, loading, hasLlm, onNext, onBack,
}: {
  config: SystemConfig | null
  loading: boolean
  hasLlm: boolean
  onNext: () => void
  onBack: () => void
}) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">LLM Provider</h2>
        <p className="text-sm text-muted-foreground">
          At least one LLM provider is required to run the content pipeline.
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center py-6"><Loader2 className="size-5 animate-spin text-muted-foreground" /></div>
      ) : (
        <div className="space-y-2">
          <ProviderRow label="Anthropic Claude" active={!!config?.api_keys.anthropic} />
          <ProviderRow label="OpenRouter" active={!!config?.api_keys.openrouter} />
        </div>
      )}

      {!loading && !hasLlm && (
        <div className="flex gap-2 p-3 rounded-md status-warning-soft border border-[var(--status-warning)]/30 text-sm">
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">No LLM configured</p>
            <p className="text-xs mt-0.5">
              Add <code className="font-mono bg-[var(--surface-2)] px-1 rounded">ANTHROPIC_API_KEY</code> or{' '}
              <code className="font-mono bg-[var(--surface-2)] px-1 rounded">OPENROUTER_API_KEY</code> to your{' '}
              <code className="font-mono bg-[var(--surface-2)] px-1 rounded">.env.local</code> and restart the server.
            </p>
          </div>
        </div>
      )}

      {!loading && hasLlm && (
        <div className="flex gap-2 p-3 rounded-md status-success-soft border border-[var(--status-success)]/30 text-sm">
          <Check className="size-4 shrink-0 mt-0.5" />
          <span>LLM provider is configured and ready.</span>
        </div>
      )}

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-24">
          <ArrowLeft className="size-3.5 mr-1" /> Back
        </Button>
        <Button className="flex-1" onClick={onNext} disabled={!hasLlm && !loading}>
          {!hasLlm && !loading ? 'Configure LLM to continue' : 'Next'}
          {hasLlm && <ChevronRight className="size-4 ml-2" />}
        </Button>
      </div>
    </div>
  )
}

function ProviderRow({ label, active }: { label: string; active: boolean }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-md border">
      <span className="text-sm font-medium">{label}</span>
      {active ? (
        <Badge className="status-success-soft border-0 text-xs">Configured</Badge>
      ) : (
        <Badge variant="outline" className="text-muted-foreground text-xs">Not set</Badge>
      )}
    </div>
  )
}

// ── Step 2: Brand ──────────────────────────────────────────────────────────────

function StepBrand({
  name, slug, topics, budget,
  onName, onSlug, onTopics, onBudget,
  onSave, saving, error, onBack,
}: {
  name: string; slug: string; topics: string; budget: string
  onName: (v: string) => void; onSlug: (v: string) => void
  onTopics: (v: string) => void; onBudget: (v: string) => void
  onSave: () => void; saving: boolean; error: string | null; onBack: () => void
}) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">Create your first brand</h2>
        <p className="text-sm text-muted-foreground">
          A brand scopes all research, content, and settings. You can add more brands later.
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="brand-name">Brand name</Label>
          <Input
            id="brand-name"
            value={name}
            onChange={e => onName(e.target.value)}
            placeholder="Acme Corp"
            autoFocus
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="brand-slug">
            Slug <span className="text-muted-foreground text-xs">(immutable after creation)</span>
          </Label>
          <Input
            id="brand-slug"
            value={slug}
            onChange={e => onSlug(e.target.value)}
            placeholder="acme-corp"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="brand-topics">
            Topics <span className="text-muted-foreground text-xs">(comma-separated, optional)</span>
          </Label>
          <Input
            id="brand-topics"
            value={topics}
            onChange={e => onTopics(e.target.value)}
            placeholder="SaaS, marketing, growth"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="brand-budget">
            Daily budget (USD) <span className="text-muted-foreground text-xs">— leave blank for unlimited</span>
          </Label>
          <div className="relative">
            <DollarSign className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              id="brand-budget"
              type="number"
              min="0"
              step="0.50"
              value={budget}
              onChange={e => onBudget(e.target.value)}
              placeholder="5.00"
              className="pl-8"
            />
          </div>
        </div>

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-24">
          <ArrowLeft className="size-3.5 mr-1" /> Back
        </Button>
        <Button
          className="flex-1"
          onClick={onSave}
          disabled={saving || !name.trim() || !slug.trim()}
        >
          {saving ? <Loader2 className="size-4 mr-2 animate-spin" /> : null}
          {saving ? 'Creating…' : 'Create Brand'}
          {!saving && <ChevronRight className="size-4 ml-2" />}
        </Button>
      </div>
    </div>
  )
}

// ── Step 3: Brand Voice ────────────────────────────────────────────────────────

function StepVoice({
  voiceFacts, onFactsSaved, onNext, onBack,
}: {
  voiceFacts: number
  onFactsSaved: (n: number) => void
  onNext: () => void
  onBack: () => void
}) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">Brand voice</h2>
        <p className="text-sm text-muted-foreground">
          Teach the system your brand's tone, principles, and examples. This step is optional.
        </p>
      </div>

      <BrandDiscovery onFactsSaved={onFactsSaved} />

      <div className="flex gap-3 pt-2">
        <Button variant="outline" onClick={onBack} className="w-24">
          <ArrowLeft className="size-3.5 mr-1" /> Back
        </Button>
        <Button
          variant={voiceFacts > 0 ? 'default' : 'outline'}
          className="flex-1"
          onClick={onNext}
        >
          {voiceFacts > 0 ? (
            <>
              Continue <ChevronRight className="size-4 ml-2" />
            </>
          ) : (
            <>
              <SkipForward className="size-3.5 mr-2" /> Skip for now
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

// ── Step 4: Research ───────────────────────────────────────────────────────────

const TIER_META = {
  premium: { label: 'Premium', badge: 'bg-[var(--brand-primary)]/15 text-[var(--brand-primary)]', desc: 'Serper + YouTube + RSS. Highest quality and volume.' },
  tavily:  { label: 'Tavily',  badge: 'status-info-soft',   desc: 'Tavily Search + RSS. 1,000 searches/month free.' },
  free:    { label: 'Free',    badge: 'status-warning-soft', desc: 'DuckDuckGo + RSS. Zero cost, works out of the box.' },
}

function StepResearch({
  config, loading, onNext, onBack,
}: {
  config: SystemConfig | null
  loading: boolean
  onNext: () => void
  onBack: () => void
}) {
  const tier = config?.research_tier ?? 'free'
  const meta = TIER_META[tier]

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">Research configuration</h2>
        <p className="text-sm text-muted-foreground">
          The pipeline researches content automatically. Here's your current setup.
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center py-6"><Loader2 className="size-5 animate-spin text-muted-foreground" /></div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 rounded-md border">
            <span className="text-sm font-medium">Active tier</span>
            <Badge className={`${meta.badge} border-0 text-xs`}>{meta.label}</Badge>
          </div>
          <p className="text-xs text-muted-foreground px-1">{meta.desc}</p>

          {tier === 'free' && (
            <div className="text-xs text-muted-foreground bg-muted/50 rounded-md p-3 space-y-1">
              <p>To upgrade:</p>
              <ul className="space-y-0.5 pl-3 list-disc">
                <li>Add <code className="font-mono">TAVILY_API_KEY</code> → Tavily tier (free plan available)</li>
                <li>Add <code className="font-mono">SERPER_API_KEY</code> → Premium tier</li>
              </ul>
              <a
                href="/settings"
                className="inline-flex items-center gap-1 text-primary hover:underline mt-1"
              >
                Configure in Settings <ExternalLink className="size-3" />
              </a>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-24">
          <ArrowLeft className="size-3.5 mr-1" /> Back
        </Button>
        <Button className="flex-1" onClick={onNext}>
          Continue <ChevronRight className="size-4 ml-2" />
        </Button>
      </div>
    </div>
  )
}

// ── Step 5: Done ───────────────────────────────────────────────────────────────

function StepDone({
  config, createdBrand, voiceFacts, onFinish,
}: {
  config: SystemConfig | null
  createdBrand: { id: string; name: string; slug: string } | null
  voiceFacts: number
  onFinish: () => void
}) {
  const hasLlm = !!(config?.api_keys.anthropic || config?.api_keys.openrouter)
  const tier = config?.research_tier ?? 'free'

  const items = [
    { label: 'LLM provider', done: hasLlm, detail: hasLlm ? 'Configured' : 'Not configured — add API key to .env.local' },
    { label: 'Brand', done: !!createdBrand, detail: createdBrand?.name ?? 'Not created' },
    { label: 'Brand voice', done: voiceFacts > 0, detail: voiceFacts > 0 ? `${voiceFacts} facts saved` : 'Not configured — add via Settings → Brand Context' },
    { label: 'Research', done: true, detail: `${TIER_META[tier].label} tier active` },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-1">Setup complete!</h2>
        <p className="text-sm text-muted-foreground">Here's a summary of what's configured.</p>
      </div>

      <div className="space-y-2">
        {items.map(({ label, done, detail }) => (
          <div key={label} className="flex items-start gap-3 p-3 rounded-md border">
            {done ? (
              <CheckCircle2 className="size-4 text-[var(--status-success)] mt-0.5 shrink-0" />
            ) : (
              <Circle className="size-4 text-muted-foreground mt-0.5 shrink-0" />
            )}
            <div>
              <p className="text-sm font-medium">{label}</p>
              <p className="text-xs text-muted-foreground">{detail}</p>
            </div>
          </div>
        ))}
      </div>

      <Button className="w-full" onClick={() => { clearWizardState(); onFinish() }}>
        Go to Dashboard
        <ChevronRight className="size-4 ml-2" />
      </Button>
    </div>
  )
}
