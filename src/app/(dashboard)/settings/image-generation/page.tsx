'use client'
import { useEffect, useState } from 'react'
import { useBrand } from '@/lib/brand-context'
import { Save, TestTube, BarChart3, ChevronLeft, ExternalLink } from 'lucide-react'
import Link from 'next/link'

const BACKENDS = [
  { value: 'replicate', label: 'Replicate (FLUX, SDXL, etc.)' },
  { value: 'openai',    label: 'OpenAI (DALL-E 3 / gpt-image-1)' },
  { value: 'openrouter', label: 'OpenRouter (FLUX, Stable Diffusion, etc.)' },
  { value: 'anthropic', label: 'Anthropic (Claude image generation)' },
  { value: 'pillo',     label: 'Pillo (carousel specialist)' },
  { value: 'mock',      label: 'Mock (local, no network — for testing)' },
]

const STYLES = ['editorial-minimal','tech-futuristic','warm-human','illustration-flat']

const MODEL_SUGGESTIONS: Record<string, string[]> = {
  replicate: ['black-forest-labs/flux-schnell','black-forest-labs/flux-dev','stability-ai/sdxl'],
  openai:    ['gpt-image-1','dall-e-3'],
  openrouter: ['black-forest-labs/flux-1-schnell','stabilityai/stable-diffusion-3-medium','black-forest-labs/flux-1-dev'],
  anthropic: ['claude-sonnet-4-20250514','claude-opus-4-20250514'],
  pillo:     ['classic','bold','minimal'],
  mock:      ['mock-v1'],
}

export default function ImageGenerationSettingsPage() {
  const { activeBrand } = useBrand()
  const [backend, setBackend] = useState('replicate')
  const [model, setModel] = useState('black-forest-labs/flux-schnell')
  const [style, setStyle] = useState('editorial-minimal')
  const [template, setTemplate] = useState('')
  const [saving, setSaving] = useState(false)
  const [testUrl, setTestUrl] = useState<string | null>(null)
  const [testErr, setTestErr] = useState<string | null>(null)
  type RecentJob = {
    id: string
    status: string
    backend: string
    model_id: string
    cost_usd?: number | null
  }
  const [stats, setStats] = useState<{
    today: { count: number; cost_usd: number }
    recent_jobs: RecentJob[]
  } | null>(null)

  useEffect(() => {
    if (!activeBrand) return
    fetch(`/api/brands`).then(r => r.json()).then((json) => {
      const rows = json.data || []
      const b = rows.find((x: {id:string}) => x.id === activeBrand.id)
      if (!b) return
      setBackend(b.image_backend ?? 'replicate')
      setModel(b.image_model ?? 'black-forest-labs/flux-schnell')
      setStyle(b.image_style_preset ?? 'editorial-minimal')
      setTemplate(b.image_prompt_template ?? '')
    })
    fetch(`/api/images/stats`).then(r => r.json()).then((json) => {
      if (json.success) setStats(json.data)
    })
  }, [activeBrand])

  async function save() {
    if (!activeBrand) return
    setSaving(true)
    await fetch(`/api/brands/${activeBrand.id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_backend: backend, image_model: model,
        image_style_preset: style,
        image_prompt_template: template || null,
      }),
    })
    setSaving(false)
  }

  async function smokeTest() {
    setTestUrl(null); setTestErr(null)
    const draftsRes = await fetch('/api/content/drafts?limit=1')
    const json = await draftsRes.json()
    const drafts = json.data || []
    if (!drafts.length) { setTestErr('No drafts available — create one first'); return }
    const r = await fetch('/api/images/generate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_id: drafts[0].id, width: 1024, height: 1024 }),
    })
    const data = await r.json()
    if (!r.ok || data.data?.status !== 'succeeded') { setTestErr(data.error?.message || data.data?.error || 'Test failed'); return }
    setTestUrl(data.data.url)
  }

  if (!activeBrand) return <div className="p-6">Select a brand first.</div>

  return (
    <div className="p-6 space-y-4 max-w-2xl">
      <header className="space-y-1">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Link href="/settings" className="inline-flex items-center gap-1 hover:text-foreground transition-colors">
            <ChevronLeft className="size-3.5" /> Settings
          </Link>
        </div>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold">Image generation</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Per-brand model + style. Overrides the global defaults. Use Replicate or OpenRouter
              for cost-efficient FLUX models, Anthropic for Claude-generated images, OpenAI for
              DALL-E, or Mock for zero-cost testing.
            </p>
          </div>
          <Link
            href="/settings/brand-assets"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0 mt-1"
          >
            Visual Assets <ExternalLink className="size-3" />
          </Link>
        </div>
      </header>

      <label className="block text-sm">
        Backend
        <select value={backend} onChange={e => { setBackend(e.target.value); setModel(MODEL_SUGGESTIONS[e.target.value][0]) }}
                className="mt-1 block w-full border rounded px-2 py-1">
          {BACKENDS.map(b => <option key={b.value} value={b.value}>{b.label}</option>)}
        </select>
      </label>

      <label className="block text-sm">
        Model ID
        <input value={model} onChange={e => setModel(e.target.value)}
               list="model-suggestions"
               className="mt-1 block w-full border rounded px-2 py-1 font-mono text-xs"/>
        <datalist id="model-suggestions">
          {MODEL_SUGGESTIONS[backend]?.map(m => <option key={m} value={m}/>)}
        </datalist>
      </label>

      <label className="block text-sm">
        Style preset
        <select value={style} onChange={e => setStyle(e.target.value)}
                className="mt-1 block w-full border rounded px-2 py-1">
          {STYLES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>

      <label className="block text-sm">
        Prompt template (optional — overrides default layout)
        <textarea value={template} onChange={e => setTemplate(e.target.value)}
                  placeholder="{brand} editorial image: {subject}. Style: {style}. {palette}"
                  rows={3} className="mt-1 block w-full border rounded px-2 py-1 font-mono text-xs"/>
        <span className="text-xs text-gray-500">
          Placeholders: {'{brand}'} {'{subject}'} {'{style}'} {'{palette}'}
        </span>
      </label>

      <div className="flex gap-2">
        <button onClick={save} disabled={saving}
                className="px-3 py-1.5 rounded bg-black text-white text-sm inline-flex items-center gap-2 disabled:opacity-50">
          <Save size={14}/> {saving ? 'Saving…' : 'Save'}
        </button>
        <button onClick={smokeTest}
                className="px-3 py-1.5 rounded border text-sm inline-flex items-center gap-2">
          <TestTube size={14}/> Test generate
        </button>
      </div>

      {testUrl && <img src={testUrl} alt="Test" className="mt-4 max-w-sm border rounded"/>}
      {testErr && <p className="text-sm text-red-600">{testErr}</p>}

      {stats && (
        <div className="border rounded p-4 space-y-3 mt-6">
          <h2 className="text-sm font-semibold inline-flex items-center gap-2">
            <BarChart3 size={14}/> Usage today
          </h2>
          <div className="flex gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Generations:</span>{' '}
              <span className="font-medium">{stats.today.count}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Cost:</span>{' '}
              <span className="font-medium">${stats.today.cost_usd.toFixed(4)}</span>
            </div>
          </div>
          {stats.recent_jobs.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Recent jobs</p>
              <div className="max-h-48 overflow-auto space-y-1">
                {stats.recent_jobs.map((job) => (
                  <div key={job.id} className="flex items-center gap-2 text-xs border-b last:border-0 pb-1">
                    <span className={`inline-block w-2 h-2 rounded-full ${
                      job.status === 'succeeded' ? 'bg-green-500' :
                      job.status === 'failed' ? 'bg-red-500' :
                      job.status === 'running' ? 'bg-amber-500' : 'bg-gray-400'
                    }`} />
                    <span className="font-mono text-[10px] text-muted-foreground">{job.id.slice(0,8)}</span>
                    <span className="capitalize">{job.status}</span>
                    <span className="text-muted-foreground">{job.backend}:{job.model_id}</span>
                    {job.cost_usd != null && <span className="text-muted-foreground">${Number(job.cost_usd).toFixed(4)}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
