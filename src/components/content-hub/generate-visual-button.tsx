'use client'
import { useState, useEffect, useCallback } from 'react'
import { Sparkles, Loader2 } from 'lucide-react'

interface GenerateVisualButtonProps {
  draftId: string
  platform: string
  onGenerated?: () => void
}

export function GenerateVisualButton({
  draftId, platform, onGenerated,
}: GenerateVisualButtonProps) {
  const [busy, setBusy] = useState<false | 'image' | 'carousel'>(false)
  const [err, setErr] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<string | null>(null)

  const pollJob = useCallback(async (id: string) => {
    try {
      const r = await fetch(`/api/images/jobs/${id}`)
      if (!r.ok) throw new Error('Poll failed')
      const data = await r.json()
      const status = data.data?.status || data.status
      setJobStatus(status)
      if (status === 'succeeded') {
        setBusy(false)
        setJobId(null)
        onGenerated?.()
        return true
      }
      if (status === 'failed') {
        setBusy(false)
        setJobId(null)
        setErr(data.data?.error || 'Generation failed')
        return true
      }
      return false
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
      setBusy(false)
      setJobId(null)
      return true
    }
  }, [onGenerated])

  useEffect(() => {
    if (!jobId) return
    const interval = setInterval(async () => {
      const done = await pollJob(jobId)
      if (done) clearInterval(interval)
    }, 2000)
    return () => clearInterval(interval)
  }, [jobId, pollJob])

  async function run(mode: 'image' | 'carousel') {
    setBusy(mode); setErr(null); setJobStatus(null)
    try {
      const path = mode === 'carousel' ? '/api/images/carousel' : '/api/images/generate'
      const body = mode === 'carousel'
        ? { draft_id: draftId, slides: 5 }
        : { draft_id: draftId, width: 1080, height: 1350 }
      const r = await fetch(path, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!r.ok) throw new Error((await r.json()).error || 'Generation failed')
      const data = await r.json()
      const id = data.data?.id || data.id
      if (!id) throw new Error('No job ID returned')
      setJobId(id)
      setJobStatus('pending')
      // Polling is driven by the useEffect interval; no inline poll needed.
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
      setBusy(false)
    }
  }

  const canCarousel = platform === 'instagram' || platform === 'linkedin'

  return (
    <div className="space-y-1">
      <div className="flex gap-1">
        <button onClick={() => run('image')} disabled={!!busy}
                className="px-2 py-1 rounded bg-black text-white text-[10px] inline-flex items-center gap-1 disabled:opacity-50">
          {busy === 'image' ? <Loader2 className="animate-spin" size={12}/> : <Sparkles size={12}/>}
          {jobId && !busy ? 'Working…' : 'Image'}
        </button>
        {canCarousel && (
          <button onClick={() => run('carousel')} disabled={!!busy}
                  className="px-2 py-1 rounded border text-[10px] inline-flex items-center gap-1 disabled:opacity-50">
            {busy === 'carousel' ? <Loader2 className="animate-spin" size={12}/> : <Sparkles size={12}/>}
            Carousel
          </button>
        )}
      </div>
      {jobStatus && jobStatus !== 'succeeded' && jobStatus !== 'failed' && (
        <p className="text-[10px] text-muted-foreground">Status: {jobStatus}</p>
      )}
      {err && <p className="text-[10px] text-red-600">{err}</p>}
    </div>
  )
}
