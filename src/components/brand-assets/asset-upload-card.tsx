'use client'
import { useState } from 'react'
import { Upload, Loader2, CheckCircle2, XCircle } from 'lucide-react'

type Kind =
  | 'logo_primary' | 'logo_mono' | 'logo_favicon'
  | 'palette' | 'font_specimen' | 'design_system_pdf'
  | 'example_newsletter' | 'example_post' | 'example_carousel'
  | 'watermark' | 'other'

export function AssetUploadCard({ brandId, onUploaded }: { brandId: string; onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [kind, setKind] = useState<Kind>('logo_primary')
  const [label, setLabel] = useState('')
  const [status, setStatus] = useState<'idle'|'uploading'|'done'|'error'>('idle')
  const [err, setErr] = useState<string | null>(null)

  async function handleUpload() {
    if (!file) return
    setStatus('uploading'); setErr(null)
    try {
      // 1) ask for a signed upload URL
      const u = await fetch(`/api/brands/${brandId}/assets/upload-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name, mime_type: file.type, bytes: file.size }),
      })
      if (!u.ok) throw new Error((await u.json()).error || 'Could not get upload URL')
      const { upload_url, storage_path } = await u.json()

      // 2) PUT the bytes directly to Supabase Storage
      const putRes = await fetch(upload_url, {
        method: 'PUT',
        headers: { 'Content-Type': file.type, 'x-upsert': 'true' },
        body: file,
      })
      if (!putRes.ok) throw new Error(`Upload failed: ${putRes.status}`)

      // 3) register metadata
      let width_px: number | undefined, height_px: number | undefined
      if (file.type.startsWith('image/')) {
        try {
          const bmp = await createImageBitmap(file)
          width_px = bmp.width; height_px = bmp.height
        } catch { /* non-fatal */ }
      }
      const regRes = await fetch(`/api/brands/${brandId}/assets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          kind, label: label || null, storage_path,
          mime_type: file.type, bytes: file.size, width_px, height_px,
        }),
      })
      if (!regRes.ok) throw new Error((await regRes.json()).error || 'Metadata registration failed')

      setStatus('done'); setFile(null); setLabel(''); onUploaded()
    } catch (e) {
      setStatus('error'); setErr(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="rounded-lg border border-dashed p-4 space-y-3">
      <h3 className="text-sm font-medium flex items-center gap-2"><Upload size={14}/> Upload asset</h3>
      <input
        type="file"
        accept="image/png,image/jpeg,image/svg+xml,image/webp,application/pdf"
        onChange={e => setFile(e.target.files?.[0] ?? null)}
        className="text-sm"
      />
      <div className="grid grid-cols-2 gap-2">
        <select className="text-sm border rounded px-2 py-1" value={kind} onChange={e => setKind(e.target.value as Kind)}>
          <option value="logo_primary">Logo (primary)</option>
          <option value="logo_mono">Logo (mono)</option>
          <option value="logo_favicon">Favicon</option>
          <option value="palette">Palette reference</option>
          <option value="font_specimen">Font specimen</option>
          <option value="design_system_pdf">Design system PDF</option>
          <option value="example_newsletter">Example newsletter</option>
          <option value="example_post">Example post</option>
          <option value="example_carousel">Example carousel</option>
          <option value="watermark">Watermark</option>
          <option value="other">Other</option>
        </select>
        <input
          type="text" placeholder="Label (optional)"
          className="text-sm border rounded px-2 py-1"
          value={label} onChange={e => setLabel(e.target.value)}
        />
      </div>
      <button
        onClick={handleUpload} disabled={!file || status === 'uploading'}
        className="px-3 py-1.5 rounded bg-black text-white text-sm disabled:opacity-50 inline-flex items-center gap-2"
      >
        {status === 'uploading' && <Loader2 className="animate-spin" size={14}/>}
        {status === 'done' && <CheckCircle2 size={14}/>}
        {status === 'error' && <XCircle size={14}/>}
        {status === 'uploading' ? 'Uploading…' : 'Upload'}
      </button>
      {err && <p className="text-xs text-red-600">{err}</p>}
    </div>
  )
}
