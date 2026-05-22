'use client'
import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useBrand } from '@/lib/brand-context'
import { AssetUploadCard } from '@/components/brand-assets/asset-upload-card'
import { PaletteEditor } from '@/components/brand-assets/palette-editor'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Image as ImgIcon, FileText, Trash2, ChevronLeft, ExternalLink, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

type Asset = {
  id: string; kind: string; label: string | null; storage_path: string;
  mime_type: string; bytes: number; width_px: number | null; height_px: number | null;
  palette_hex: string[] | null; metadata: Record<string, unknown>; created_at: string;
}

export default function BrandAssetsPage() {
  const { activeBrand, isLoading: brandLoading } = useBrand()
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [signedUrls, setSignedUrls] = useState<Record<string, string>>({})
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [assetToDelete, setAssetToDelete] = useState<Asset | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!activeBrand) return
    setLoading(true)
    setLoadError(null)
    try {
      const res = await fetch(`/api/brands/${activeBrand.id}/assets`)
      const json = await res.json()
      // The route returns the canonical {success, data} envelope
      // (see src/app/api/brands/[id]/assets/route.ts:30 → jsonResponse(data || []))
      // — always read .data, never the bare body.
      const data: Asset[] = Array.isArray(json?.data) ? json.data : []
      setAssets(data)
      // Fetch signed preview URLs for images
      const entries = await Promise.all(
        data.filter(a => a.mime_type.startsWith('image/')).map(async a => {
          const u = await fetch(`/api/brands/${activeBrand.id}/assets/${a.id}/preview`)
            .then(r => r.ok ? r.json() : null)
          return [a.id, u?.data?.url ?? ''] as const
        })
      )
      setSignedUrls(Object.fromEntries(entries))
    } catch {
      setLoadError('Could not load brand assets. Try refreshing the page.')
      setAssets([])
    }
    setLoading(false)
  }, [activeBrand])

  useEffect(() => { refresh() }, [refresh])

  const initiateDelete = (asset: Asset) => {
    setAssetToDelete(asset)
    setDeleteError(null)
    setDeleteConfirmOpen(true)
  }

  const confirmDelete = async () => {
    if (!activeBrand || !assetToDelete) return
    setDeleting(true)
    setDeleteError(null)
    try {
      const res = await fetch(`/api/brands/${activeBrand.id}/assets/${assetToDelete.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      setDeleteConfirmOpen(false)
      setAssetToDelete(null)
      refresh()
    } catch {
      setDeleteError('Delete failed. The asset is still on the server — try again.')
    } finally {
      setDeleting(false)
    }
  }

  // Wait for the brand context to hydrate from localStorage before deciding
  // there's no active brand — otherwise the "Select a brand first" message
  // flashes on every cold load.
  if (brandLoading) {
    return <div className="p-6 text-sm text-muted-foreground">Loading brand…</div>
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

      {loading && <p className="text-sm text-ink-subtle">Loading…</p>}
      {loadError && (
        <p className="text-sm text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
          {loadError}
        </p>
      )}

      {Object.entries(grouped).map(([kind, list]) => (
        <section key={kind} className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-subtle">
            {kind.replace(/_/g,' ')}
          </h2>
          <div className="grid grid-cols-3 gap-3">
            {list.map(a => (
              <div key={a.id} className="border rounded p-3 space-y-2">
                {a.mime_type.startsWith('image/') && signedUrls[a.id]
                  ? <img src={signedUrls[a.id]} alt={a.label ?? a.kind}
                         className="w-full h-32 object-contain bg-[var(--surface-1)] rounded"/>
                  : <div className="w-full h-32 bg-[var(--surface-1)] rounded flex items-center justify-center text-ink-tertiary">
                      {a.mime_type === 'application/pdf' ? <FileText size={32}/> : <ImgIcon size={32}/>}
                    </div>}
                <div className="text-xs">
                  <div className="font-medium truncate">{a.label || '—'}</div>
                  <div className="text-ink-subtle">{(a.bytes/1024).toFixed(0)} KB {a.width_px ? `· ${a.width_px}×${a.height_px}` : ''}</div>
                </div>
                {a.kind === 'palette' && (
                  <PaletteEditor brandId={activeBrand.id} assetId={a.id} initial={a.palette_hex ?? []}/>
                )}
                <button onClick={() => initiateDelete(a)}
                        className="text-xs text-[var(--status-error)] inline-flex items-center gap-1">
                  <Trash2 size={12}/> Delete
                </button>
              </div>
            ))}
          </div>
        </section>
      ))}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent className="sm:max-w-md border border-destructive/20 bg-background/95 backdrop-blur-md">
          <DialogHeader className="flex flex-row items-start gap-3 space-y-0 pb-2">
            <div className="p-2 rounded-full bg-destructive/10 text-destructive mt-0.5">
              <Trash2 className="size-5" />
            </div>
            <div className="space-y-1">
              <DialogTitle className="text-lg font-semibold text-destructive">
                Delete Asset
              </DialogTitle>
              <p className="text-xs text-muted-foreground">
                This action is permanent and cannot be undone.
              </p>
            </div>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <p className="text-sm">
              Are you sure you want to delete <strong className="font-semibold text-foreground">"{assetToDelete?.label || assetToDelete?.kind || 'this asset'}"</strong>?
            </p>
            <div className="rounded-lg bg-muted/50 border p-3 space-y-1.5 text-xs text-muted-foreground">
              <p className="font-medium text-foreground">Details:</p>
              <ul className="list-disc pl-4 space-y-1">
                <li>Kind: <span className="capitalize text-foreground">{assetToDelete?.kind.replace(/_/g, ' ')}</span></li>
                {assetToDelete?.mime_type && <li>Type: <span className="font-mono text-foreground">{assetToDelete.mime_type}</span></li>}
                {assetToDelete?.bytes && <li>Size: <span className="font-mono text-foreground">{(assetToDelete.bytes / 1024).toFixed(1)} KB</span></li>}
              </ul>
            </div>
            {deleteError && (
              <p className="text-xs font-medium text-destructive bg-destructive/5 border border-destructive/10 rounded-md p-2">
                {deleteError}
              </p>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setDeleteConfirmOpen(false)}
              disabled={deleting}
              className="sm:order-first"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={deleting}
              className="bg-destructive hover:bg-destructive/90 text-destructive-foreground font-medium"
            >
              {deleting ? <Loader2 className="size-4 animate-spin mr-2" /> : null}
              {deleting ? 'Deleting...' : 'Delete Asset'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
