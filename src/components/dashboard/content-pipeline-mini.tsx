import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

const stages = [
  { label: 'Discovery', count: 0 },
  { label: 'Scored', count: 0 },
  { label: 'Approved', count: 0 },
  { label: 'Published', count: 0 },
] as const

export function ContentPipelineMini() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Pipeline Contenuti</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          {stages.map((stage, index) => (
            <div key={stage.label} className="flex items-center">
              <div className="text-center">
                <p className="text-2xl font-bold">{stage.count}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {stage.label}
                </p>
              </div>
              {index < stages.length - 1 && (
                <span className="mx-3 text-muted-foreground">&rarr;</span>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
