import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { logout } from '@/app/(auth)/login/actions'
import { StagingBar } from '@/components/layout/staging-bar'
import { Sidebar } from '@/components/layout/sidebar'
import { URLBar } from '@/components/layout/url-bar'
import { APISpendRow } from '@/components/layout/api-spend-row'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Staging bar — full width at the very top */}
      <StagingBar />

      {/* Below: sidebar + main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — fixed width */}
        <Sidebar logoutAction={logout} />

        {/* Main content area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* URL bar + API spend row */}
          <div className="space-y-2 p-4 pb-0">
            <URLBar />
            <APISpendRow />
          </div>

          {/* Page content */}
          <div className="flex-1 overflow-y-auto p-4">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
