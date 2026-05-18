'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Play, Link2 } from 'lucide-react'

/**
 * URLBar — Quick URL analysis input.
 *
 * Linear text-input spec applied:
 *  - Background: surface-1
 *  - Border: 1px hairline
 *  - Rounded: md (8px)
 *  - Focus: hairline-strong
 *  - Padding: 8px 12px
 */
export function URLBar() {
  const router = useRouter()
  const [value, setValue] = useState('')

  const submit = () => {
    const trimmed = value.trim()
    if (!trimmed) return
    router.push(`/content-hub?url=${encodeURIComponent(trimmed)}`)
    setValue('')
  }

  return (
    <div
      className="h-9 flex items-center gap-2 px-3 rounded-md border transition-colors focus-within:border-hairline-strong"
      style={{
        background: 'var(--surface-1)',
        borderColor: 'var(--hairline)',
      }}
    >
      <Link2 className="h-3.5 w-3.5 shrink-0 text-ink-subtle" />
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && submit()}
        placeholder="Paste URL for quick analysis..."
        className="flex-1 bg-transparent text-sm text-ink placeholder:text-ink-tertiary outline-none"
        style={{ letterSpacing: '-0.05px' }}
      />
      <button
        onClick={submit}
        disabled={!value.trim()}
        className="size-6 rounded flex items-center justify-center text-ink-subtle hover:text-ink hover:bg-surface-2 disabled:opacity-40 disabled:hover:bg-transparent transition-colors"
        title="Analyze URL"
      >
        <Play className="h-3 w-3" />
      </button>
    </div>
  )
}
