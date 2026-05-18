'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Trash2, Loader2, Film } from 'lucide-react'
import { GenerateVisualButton } from '@/components/content-hub/generate-visual-button'
import { PublishButton } from '@/components/content-hub/publish-button'
import { useBrand } from '@/lib/brand-context'

interface Draft {
  id: string
  title: string | null
  body: string | null
  platform: string
  content_type: string
  status: string
  version: number | null
  god_mode_result: unknown
  created_at: string | null
  media_urls: string[] | null
}

export default function DraftDetailPage() {
  const params = useParams()
  const router = useRouter()
  const draftId = params.id as string
  const { activeBrand } = useBrand()
  const [draft, setDraft] = useState<Draft | null>(null)
  const [loading, setLoading] = useState(true)
  const [deletingMedia, setDeletingMedia] = useState<string | null>(null)
  const [convertingReel, setConvertingReel] = useState(false)
  const [reelVideoId, setReelVideoId] = useState<string | null>(null)

  const fetchDraft = useCallback(async () => {
    try {
      const resp = await fetch(`/api/content/drafts/${draftId}`)
      const json = await resp.json()
      if (json.success) setDraft(json.data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [draftId])

  useEffect(() => { fetchDraft() }, [fetchDraft])

  async function convertToReel() {
    if (!draft?.media_urls?.length) return
    setConvertingReel(true)
    try {
      const res = await fetch('/api/video/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_slug: 'carousel-to-reel',
          render_props: {
            slide_urls: JSON.stringify(draft.media_urls),
            brand_name: activeBrand?.name ?? '',
          },
          title: `${draft.title ?? 'Carousel'} — Reel`,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setReelVideoId(data.video_id)
      }
    } finally {
      setConvertingReel(false)
    }
  }

  async function deleteMedia(url: string) {
    if (!draft) return
    setDeletingMedia(url)
    try {
      const updated = (draft.media_urls || []).filter((u) => u !== url)
      const resp = await fetch(`/api/content/drafts/${draftId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ media_urls: updated }),
      })
      if (resp.ok) {
        setDraft((d) => (d ? { ...d, media_urls: updated } : d))
      }
    } finally {
      setDeletingMedia(null)
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="animate-spin size-4" />
          Loading draft…
        </div>
      </div>
    )
  }

  if (!draft) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Draft not found.</p>
        <Button variant="ghost" onClick={() => router.push('/content-hub')}>
          <ArrowLeft className="size-4 mr-1" /> Back to Content Hub
        </Button>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => router.push('/content-hub')}>
          <ArrowLeft className="size-4 mr-1" /> Back
        </Button>
        <Badge variant="secondary">{draft.platform.toUpperCase()}</Badge>
        <Badge variant="outline">{draft.status.toUpperCase().replace('_', ' ')}</Badge>
      </div>

      <div>
        <h1 className="text-2xl font-bold">{draft.title || 'Untitled'}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {draft.content_type} · v{draft.version ?? 1}
        </p>
      </div>

      <div className="prose prose-sm max-w-none">
        <p className="whitespace-pre-wrap">{draft.body}</p>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap items-center gap-3">
        <PublishButton draftId={draft.id} onPublished={fetchDraft} />
        <GenerateVisualButton
          draftId={draft.id}
          platform={draft.platform}
          onGenerated={fetchDraft}
        />
        {draft.content_type === 'carousel' && (draft.media_urls?.length ?? 0) >= 2 && (
          <Button
            variant="outline"
            size="sm"
            onClick={convertToReel}
            disabled={convertingReel || !!reelVideoId}
          >
            {convertingReel
              ? <Loader2 className="size-4 mr-1 animate-spin" />
              : <Film className="size-4 mr-1" />}
            {reelVideoId ? 'Reel queued ✓' : 'Convert to reel'}
          </Button>
        )}
        {reelVideoId && (
          <a
            href="/videos"
            className="text-xs text-muted-foreground hover:underline"
          >
            View in Videos →
          </a>
        )}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Media</h2>
        </div>

        {(!draft.media_urls || draft.media_urls.length === 0) && (
          <p className="text-sm text-muted-foreground">No media yet. Generate an image above.</p>
        )}

        {draft.media_urls && draft.media_urls.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {draft.media_urls.map((url, idx) => (
              <div key={idx} className="relative group rounded-lg border overflow-hidden">
                <img src={url} alt={`Media ${idx + 1}`} className="w-full h-40 object-cover" />
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                  <Button
                    variant="ghost"
                    size="xs"
                    className="text-white"
                    onClick={() => deleteMedia(url)}
                    disabled={deletingMedia === url}
                  >
                    {deletingMedia === url ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <Trash2 className="size-3" />
                    )}
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
