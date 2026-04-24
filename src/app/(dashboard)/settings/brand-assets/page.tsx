'use client'
import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useBrand } from '@/lib/brand-context'
import { AssetUploadCard } from '@/components/brand-assets/asset-upload-card'
import { PaletteEditor } from '@/components/brand-assets/palette-editor'
import { Image as ImgIcon, FileText, Trash2, ChevronLeft, ExternalLink } from 'lucide-react'

type Asset = {
  id: string; kind: string; label: string | null; storage_path: string;
  mime_type: string; bytes: number; width_px: number | null; height_px: number | null;
  palette_hex: string[] | null; metadata: Record<string, unknown>; created_at: string;
}

export default function BrandAssetsPage() {
  const { activeBrand } = useBrand()
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [signedUrls, setSignedUrls] = useState<Record<string, string>>({})

  const refresh = useCallback(async () => {
    if (!activeBrand) return
    setLoading(true)
    const res = await fetch(`/api/brands/${activeBrand.id}/assets`)
    const data: Asset[] = await res.json()
    setAssets(data)
    // Fetch signed preview URLs for images
    const entries = await Promise.all(data.filter(a => a.mime_type.startsWith('image/')).map(async a => {
      const u = await fetch(`/api/brands/${activeBrand.id}/assets/${a.id}/preview`).then(r => r.ok ? r.json() : null)
      return [a.id, u?.data?.url ?? ''] as const
    }))
    setSignedUrls(Object.fromEntries(entries))
    setLoading(false)
  }, [activeBrand])

  useEffect(() => { refresh() }, [refresh])

  async function remove(id: string) {
    if (!activeBrand) return
    if (!confirm('Delete this asset?')) return
    await fetch(`/api/brands/${activeBrand.id}/assets/${id}`, { method: 'DELETE' })
    refresh()
  }

  if (!activeBrand) return <div className="p-6">Select a brand first.</div>

  const grouped = assets.reduce<Record<string, Asset[]>>((acc, a) => {
    (acc[a.kind] ||= []).push(a); return acc
  }, {})

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <header className="space-y-1">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Link href="/settings" className="inline-flex items-center gap-1 hover:text-foreground transition-colors">
            <ChevronLeft className="size-3.5" /> Settings
          </Link>
        </div>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold">Brand Visual Assets</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Logos, palette, design system, example content — long-term editable. Used by the image
              generator and by text agents when they need visual grounding.
            </p>
          </div>
          <Link
            href="/settings/image-generation"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0 mt-1"
          >
            Image Generation <ExternalLink className="size-3" />
          </Link>
        </div>
      </header>

      <AssetUploadCard brandId={activeBrand.id} onUploaded={refresh} />

      {loading && <p className="text-sm text-gray-500">Loading…</p>}

      {Object.entries(grouped).map(([kind, list]) => (
        <section key={kind} className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600">
            {kind.replace(/_/g,' ')}
          </h2>
          <div className="grid grid-cols-3 gap-3">
            {list.map(a => (
              <div key={a.id} className="border rounded p-3 space-y-2">
                {a.mime_type.startsWith('image/') && signedUrls[a.id]
                  ? <img src={signedUrls[a.id]} alt={a.label ?? a.kind}
                         className="w-full h-32 object-contain bg-gray-50 rounded"/>
                  : <div className="w-full h-32 bg-gray-50 rounded flex items-center justify-center text-gray-400">
                      {a.mime_type === 'application/pdf' ? <FileText size={32}/> : <ImgIcon size={32}/>}
                    </div>}
                <div className="text-xs">
                  <div className="font-medium truncate">{a.label || '—'}</div>
                  <div className="text-gray-500">{(a.bytes/1024).toFixed(0)} KB {a.width_px ? `· ${a.width_px}×${a.height_px}` : ''}</div>
                </div>
                {a.kind === 'palette' && (
                  <PaletteEditor brandId={activeBrand.id} assetId={a.id} initial={a.palette_hex ?? []}/>
                )}
                <button onClick={() => remove(a.id)}
                        className="text-xs text-red-600 inline-flex items-center gap-1">
                  <Trash2 size={12}/> Delete
                </button>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
