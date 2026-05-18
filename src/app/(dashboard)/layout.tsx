import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { logout } from '@/app/(auth)/login/actions'
import { StagingBar } from '@/components/layout/staging-bar'
import { Sidebar } from '@/components/layout/sidebar'
import { URLBar } from '@/components/layout/url-bar'
import { APISpendRow } from '@/components/layout/api-spend-row'
import { BrandProvider } from '@/lib/brand-context'

/**
 * Dashboard shell — Linear app layout.
 *
 * Structure:
 *   ┌─ StagingBar (coral, 28px)  ──────────────────────┐
 *   ├─────────┬──────────────────────────────────────┤
 *   │ Sidebar │ Top context bar (URL + API spend)    │
 *   │ 240px   ├──────────────────────────────────────┤
 *   │ canvas  │ Main content (canvas bg, padded)     │
 *   └─────────┴──────────────────────────────────────┘
 *
 * Canvas everywhere — sidebar and main share #050505.
 * Hairline border between sidebar and main creates the only divider.
 */
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
    <BrandProvider>
      <div className="h-screen flex flex-col overflow-hidden bg-background">
        <StagingBar />

        <div className="flex flex-1 overflow-hidden">
          <Sidebar logoutAction={logout} />

          <main className="flex-1 flex flex-col overflow-hidden">
            {/* Top context bar — URL input + API spend pills */}
            <div className="border-b border-hairline px-6 py-3 space-y-2 shrink-0">
              <URLBar />
              <APISpendRow />
            </div>

            {/* Page content — generous padding (Linear: section rhythm) */}
            <div className="flex-1 overflow-y-auto px-6 py-6">
              {children}
            </div>
          </main>
        </div>
      </div>
    </BrandProvider>
  )
}
