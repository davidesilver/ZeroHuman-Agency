'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LogOut } from 'lucide-react'
import { navigationItems } from '@/lib/navigation'
import { BrandSwitcher } from './brand-switcher'

/**
 * Sidebar — Dark contrast anchor on light cream main area.
 *
 * Uses dedicated sidebar tokens (--sidebar-*) so it stays dark
 * while the rest of the app is light (Sentry/YouTube Studio pattern).
 *
 * - Width: 240px
 * - Background: --sidebar (#1c1c24)
 * - Border-right: --sidebar-border (#2e2e38)
 * - Active item: --sidebar-accent bg + coral left-border
 * - Brand mark: coral square + white "Z"
 */
export function Sidebar({ logoutAction }: { logoutAction: () => Promise<void> }) {
  const pathname = usePathname()

  return (
    <aside
      className="w-60 h-full flex flex-col"
      style={{
        background: 'var(--sidebar)',
        borderRight: '1px solid var(--sidebar-border)',
      }}
    >
      {/* ── Brand mark + wordmark ───────────────────────────────────── */}
      <div className="px-4 py-4 flex items-center gap-3">
        <Image
          src="/brand/zerohuman-mark-reverse.svg"
          alt="ZeroHuman"
          width={32}
          height={32}
          className="shrink-0"
        />
        <div className="flex flex-col min-w-0">
          <span
            className="text-sm font-semibold truncate"
            style={{ color: 'var(--sidebar-foreground)', letterSpacing: '-0.01em' }}
          >
            ZeroHuman
          </span>
          <span
            className="text-[11px] font-semibold uppercase tracking-[0.15em]"
            style={{ color: 'rgba(226,226,230,0.45)' }}
          >
            Content Engine
          </span>
        </div>
      </div>

      {/* ── Brand switcher ──────────────────────────────────────────── */}
      <BrandSwitcher />

      {/* ── Navigation ──────────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto px-2 py-2">
        {navigationItems.map((item, index) => {
          if ('type' in item && item.type === 'separator') {
            return (
              <div
                key={index}
                className="text-[11px] font-semibold uppercase tracking-[0.15em] mt-5 mb-1.5 px-3"
                style={{ color: 'rgba(226,226,230,0.40)' }}
              >
                {item.label}
              </div>
            )
          }
          if (!('href' in item)) return null

          const Icon = item.icon
          const isActive = pathname === item.href

          return (
            <Link
              key={item.href}
              href={item.href}
              className="relative flex items-center gap-3 rounded-md px-3 py-1.5 text-sm transition-colors duration-100"
              style={{
                color: isActive ? 'var(--sidebar-foreground)' : 'rgba(226,226,230,0.60)',
                background: isActive ? 'var(--sidebar-accent)' : 'transparent',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = 'var(--sidebar-accent)'
                  e.currentTarget.style.color = 'var(--sidebar-foreground)'
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = 'transparent'
                  e.currentTarget.style.color = 'rgba(226,226,230,0.60)'
                }
              }}
            >
              {/* Active indicator: 2px coral left border */}
              {isActive && (
                <span
                  className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r"
                  style={{ background: 'var(--brand-primary)' }}
                />
              )}
              <Icon
                className="h-4 w-4 shrink-0"
                style={isActive ? { color: 'var(--brand-primary)' } : undefined}
              />
              <span className="font-medium truncate">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* ── Logout (pinned bottom) ─────────────────────────────────── */}
      <div className="p-2" style={{ borderTop: '1px solid var(--sidebar-border)' }}>
        <form action={logoutAction}>
          <button
            type="submit"
            className="flex w-full items-center gap-3 rounded-md px-3 py-1.5 text-sm transition-colors"
            style={{ color: 'rgba(226,226,230,0.50)' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--sidebar-accent)'
              e.currentTarget.style.color = 'var(--sidebar-foreground)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = 'rgba(226,226,230,0.50)'
            }}
          >
            <LogOut className="h-4 w-4 shrink-0" />
            <span className="font-medium">Logout</span>
          </button>
        </form>
      </div>
    </aside>
  )
}
