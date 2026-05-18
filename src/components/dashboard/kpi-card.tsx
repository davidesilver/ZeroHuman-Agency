import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'

/**
 * KPICard — Dashboard metric tile.
 *
 * Layout:
 *   - Eyebrow label (uppercase, +0.15em tracking) — Linear/Sentry pattern
 *   - Display value (Linear display-md spec: 40px / 600 / -1.0px)
 *   - Subtitle (caption, ink-subtle)
 *   - Trend pill (top-right, status-success-soft chip)
 *
 * Destructive variant: tints value + adds hairline highlight
 */
interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: string
  variant?: 'default' | 'destructive'
}

export function KPICard({ title, value, subtitle, trend, variant = 'default' }: KPICardProps) {
  return (
    <Card
      className={cn(
        'gap-2',
        variant === 'destructive' && 'border-[var(--status-error)]/30'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="eyebrow text-[10px]">{title}</span>
        {trend && (
          <span className="status-success-soft text-[10px] font-medium px-1.5 py-0.5 rounded">
            {trend}
          </span>
        )}
      </div>
      <div
        className={cn(
          'font-semibold leading-none',
          variant === 'destructive' ? 'text-[var(--status-error)]' : 'text-ink'
        )}
        style={{
          fontSize: '32px',
          letterSpacing: '-0.8px',
          lineHeight: 1.1,
        }}
      >
        {value}
      </div>
      {subtitle && (
        <p className="text-xs text-ink-subtle mt-0.5">
          {subtitle}
        </p>
      )}
    </Card>
  )
}
