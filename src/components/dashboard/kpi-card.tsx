import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: string
  variant?: 'default' | 'destructive'
}

export function KPICard({ title, value, subtitle, trend, variant = 'default' }: KPICardProps) {
  return (
    <Card className={cn(variant === 'destructive' && 'border-destructive/50')}>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className={cn('text-3xl font-bold', variant === 'destructive' && 'text-destructive')}>{value}</p>
            <p className="text-sm text-muted-foreground mt-1">{title}</p>
            {subtitle && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
          {trend && (
            <span className="text-xs font-medium text-brand-secondary">
              {trend}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
