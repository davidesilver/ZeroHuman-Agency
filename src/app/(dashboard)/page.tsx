import { KPICard } from '@/components/dashboard/kpi-card'
import { ActivityLog } from '@/components/dashboard/activity-log'
import { AgentStatus } from '@/components/dashboard/agent-status'
import { ContentPipelineMini } from '@/components/dashboard/content-pipeline-mini'

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>

      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPICard title="Contenuti in pipeline" value={0} />
        <KPICard title="Pubblicati questa settimana" value={0} />
        <KPICard title="Agenti attivi" value="0 / 5" />
        <KPICard title="Spesa API oggi" value="€0.00" />
      </div>

      {/* Pipeline mini */}
      <div className="mb-6">
        <ContentPipelineMini />
      </div>

      {/* Activity log + Agent status */}
      <div className="grid grid-cols-2 gap-4">
        <ActivityLog />
        <AgentStatus />
      </div>
    </div>
  )
}
