'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LogOut } from 'lucide-react'
import { navigationItems } from '@/lib/navigation'
import { BrandSwitcher } from './brand-switcher'

/**
 * Sidebar — Linear.app pattern, ZeroHuman recolor.
 *
 * - Width: 240px (Linear: ~220-240px expanded)
 * - Background: canvas (#050505) — deepest surface, anchors the page
 * - Border-right: hairline (#23252a) — Linear's signature 1px separator
 * - Brand mark: 32px coral square with ZeroHuman wordmark
 * - Brand eyebrow: uppercase, +0.15em tracking (Linear signature)
 * - Groups: eyebrow labels for nav sections (Linear/YouTube Studio pattern)
 * - Active item: surface-1 bg + 2px coral left-border (Linear pattern)
 * - Hover: surface-1 bg, no transition flash
 * - Logout: bottom-pinned, hairline divider above
 */
export function Sidebar({ logoutAction }: { logoutAction: () => Promise<void> }) {
  const pathname = usePathname()

  return (
    <aside className="w-60 surface-canvas h-full flex flex-col border-r border-hairline">
      {/* ── Brand mark + wordmark ───────────────────────────────────── */}
      <div className="px-4 py-4 flex items-center gap-3">
        <div
          className="size-8 rounded-md flex items-center justify-center shrink-0"
          style={{ background: 'var(--brand-primary)' }}
        >
          <span className="text-sm font-bold text-[#050505]" style={{ letterSpacing: '-0.04em' }}>
            Z
          </span>
        </div>
        <div className="flex flex-col min-w-0">
          <span className="text-sm font-semibold text-ink truncate" style={{ letterSpacing: '-0.01em' }}>
            ZeroHuman
          </span>
          <span className="eyebrow text-[10px]">Content Engine</span>
        </div>
      </div>

      {/* ── Brand switcher ──────────────────────────────────────────── */}
      <BrandSwitcher />

      {/* ── Navigation ──────────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto px-2 py-2">
        {navigationItems.map((item, index) => {
          if ('type' in item && item.type === 'separator') {
            return (
              <div key={index} className="eyebrow mt-5 mb-1.5 px-3 text-[10px]">
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
              className={`
                relative flex items-center gap-3 rounded-md px-3 py-1.5 text-sm
                transition-colors duration-100
                ${isActive
                  ? 'bg-surface-1 text-ink'
                  : 'text-ink-muted hover:text-ink hover:bg-surface-1'
                }
              `}
            >
              {/* Active indicator: 2px coral left border (Linear pattern) */}
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

      {/* ── Logout (pinned bottom, hairline divider above) ─────────── */}
      <div className="p-2 border-t border-hairline">
        <form action={logoutAction}>
          <button
            type="submit"
            className="flex w-full items-center gap-3 rounded-md px-3 py-1.5 text-sm text-ink-subtle hover:text-ink hover:bg-surface-1 transition-colors"
          >
            <LogOut className="h-4 w-4 shrink-0" />
            <span className="font-medium">Logout</span>
          </button>
        </form>
      </div>
    </aside>
  )
}
