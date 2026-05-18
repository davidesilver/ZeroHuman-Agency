import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'

/**
 * KPICard — Dashboard metric tile.
 *
 * Light-mode: white card + Miro warm shadow (from Card component).
 * Stripe tnum applied to the display value for column alignment.
 * Miro 64px stat display pattern for key metrics.
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
      {/* Stripe tabular figures — numbers align in columns */}
      <div
        className={cn(
          'tabular font-semibold leading-none',
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
