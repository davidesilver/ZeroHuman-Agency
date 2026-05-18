'use client'

import type { LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface EmptyStateProps {
  icon?: LucideIcon
  message: string
  actionLabel?: string
  onAction?: () => void
}

/**
 * Standardized empty state display for lists/tables.
 */
export function EmptyState({ icon: Icon, message, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {Icon && <Icon className="h-8 w-8 text-muted-foreground/50 mb-3" />}
      <p className="text-sm text-muted-foreground">{message}</p>
      {actionLabel && onAction && (
        <Button size="sm" variant="outline" className="mt-3" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
