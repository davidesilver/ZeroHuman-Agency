import { Card, CardContent } from '@/components/ui/card'

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: string
}

export function KPICard({ title, value, subtitle, trend }: KPICardProps) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-3xl font-bold">{value}</p>
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
