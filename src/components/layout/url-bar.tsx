'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

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
    <div className="h-10 bg-brand-accent flex items-center gap-2 px-4 rounded-md">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && submit()}
        placeholder="Paste URL for quick analysis..."
        className="h-7 flex-1 border-none bg-white/90 text-black placeholder:text-black/50 text-sm"
      />
      <Button
        size="sm"
        variant="ghost"
        onClick={submit}
        disabled={!value.trim()}
        className="h-7 w-7 p-0 text-black hover:bg-black/10"
      >
        <Play className="h-4 w-4" />
      </Button>
    </div>
  )
}
