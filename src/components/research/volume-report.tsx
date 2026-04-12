'use client'

interface RetrieverStat {
  name: string
  count: number
  color: string
}

interface VolumeReportProps {
  total: number
  stats: RetrieverStat[]
}

export function VolumeReport({ total, stats }: VolumeReportProps) {
  const maxCount = Math.max(...stats.map((s) => s.count), 1)

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-sm font-medium text-muted-foreground">Volume Report</span>
        <span className="text-2xl font-bold">{total}</span>
      </div>
      <div className="space-y-2">
        {stats.map((stat) => (
          <div key={stat.name} className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground w-28 truncate">{stat.name}</span>
            <div className="flex-1 h-4 bg-secondary rounded-sm overflow-hidden">
              <div
                className="h-full rounded-sm transition-all"
                style={{
                  width: `${(stat.count / maxCount) * 100}%`,
                  backgroundColor: stat.color,
                }}
              />
            </div>
            <span className="text-xs font-medium w-8 text-right">{stat.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
