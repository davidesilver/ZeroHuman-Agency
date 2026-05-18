'use client'

import { useEffect, useState, type ReactNode } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { AlertTriangle, Loader2 } from 'lucide-react'

interface FeatureGateProps {
  flag: string
  children: ReactNode
  brandId?: string | null
  /** Custom message when feature is disabled */
  disabledMessage?: string
}

/**
 * Gates children behind a per-brand feature flag.
 * Shows a "not enabled" card when the flag is OFF, or renders children when ON.
 */
export function FeatureGate({
  flag,
  children,
  brandId,
  disabledMessage,
}: FeatureGateProps) {
  const [state, setState] = useState<'loading' | 'enabled' | 'disabled'>('loading')

  useEffect(() => {
    if (!brandId) {
      setState('disabled')
      return
    }

    let cancelled = false
    async function check() {
      try {
        const res = await fetch(
          `/api/feature-flags?key=${encodeURIComponent(flag)}&brand_id=${encodeURIComponent(brandId!)}`
        )
        if (!res.ok) {
          setState('disabled')
          return
        }
        const data = await res.json()
        if (!cancelled) {
          setState(data.value ? 'enabled' : 'disabled')
        }
      } catch {
        if (!cancelled) setState('disabled')
      }
    }

    check()
    return () => { cancelled = true }
  }, [flag, brandId])

  if (state === 'loading') {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (state === 'disabled') {
    return (
      <div className="p-6 max-w-lg mx-auto mt-12">
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
            <AlertTriangle className="h-8 w-8 text-muted-foreground" />
            <h3 className="text-sm font-medium">Feature not enabled</h3>
            <p className="text-xs text-muted-foreground max-w-sm">
              {disabledMessage ??
                `This feature is not enabled for your brand. An admin can enable it from Settings → Feature Flags.`}
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return <>{children}</>
}
