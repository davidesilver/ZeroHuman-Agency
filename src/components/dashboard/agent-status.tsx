import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const agents = [
  { name: 'ResearchBot', status: 'Offline' },
  { name: 'ScoringAgent', status: 'Offline' },
  { name: 'WriterAgent', status: 'Offline' },
  { name: 'EditorAgent', status: 'Offline' },
  { name: 'FactChecker', status: 'Offline' },
] as const

export function AgentStatus() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Stato Agenti</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {agents.map((agent) => (
            <li
              key={agent.name}
              className="flex items-center justify-between"
            >
              <span className="text-sm font-medium">{agent.name}</span>
              <Badge variant="secondary" className="text-xs">
                {agent.status}
              </Badge>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
