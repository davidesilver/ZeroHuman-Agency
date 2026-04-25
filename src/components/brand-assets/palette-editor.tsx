'use client'
import { useState } from 'react'
import { Plus, Trash2, Save } from 'lucide-react'

export function PaletteEditor({
  brandId, assetId, initial,
}: { brandId: string; assetId: string; initial: string[] }) {
  const [colors, setColors] = useState<string[]>(initial.length ? initial : ['#000000'])
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    await fetch(`/api/brands/${brandId}/assets/${assetId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ palette_hex: colors }),
    })
    setSaving(false)
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {colors.map((c, i) => (
          <div key={i} className="flex items-center gap-1 border rounded px-2 py-1">
            <input
              type="color" value={c}
              onChange={e => { const next = [...colors]; next[i] = e.target.value; setColors(next) }}
              className="w-6 h-6 cursor-pointer border-0 p-0"
            />
            <span className="text-xs font-mono">{c}</span>
            <button onClick={() => setColors(colors.filter((_, j) => j !== i))}
                    className="text-gray-400 hover:text-red-600"><Trash2 size={12}/></button>
          </div>
        ))}
        <button onClick={() => setColors([...colors, '#888888'])}
                className="border border-dashed rounded px-2 py-1 text-xs inline-flex items-center gap-1">
          <Plus size={12}/> Add
        </button>
      </div>
      <button onClick={save} disabled={saving}
              className="px-3 py-1 rounded bg-black text-white text-xs inline-flex items-center gap-1 disabled:opacity-50">
        <Save size={12}/> {saving ? 'Saving…' : 'Save palette'}
      </button>
    </div>
  )
}
