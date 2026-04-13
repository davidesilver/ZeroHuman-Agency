'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LogOut } from 'lucide-react'
import { navigationItems } from '@/lib/navigation'
import { BrandSwitcher } from './brand-switcher'

interface SidebarProps {
  logoutAction: () => Promise<void>
}

export function Sidebar({ logoutAction }: SidebarProps) {
  const pathname = usePathname()

  return (
    <aside className="w-60 bg-sidebar h-full flex flex-col">
      {/* Brand */}
      <div className="px-4 py-5">
        <h2 className="text-lg font-semibold text-white">Content Engine</h2>
      </div>

      {/* Brand Switcher */}
      <BrandSwitcher />

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2">
        {navigationItems.map((item, index) => {
          if ('type' in item && item.type === 'separator') {
            return (
              <div
                key={index}
                className="mt-6 mb-2 px-4 text-xs font-semibold uppercase tracking-wider text-gray-500"
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
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? 'border-l-2 border-brand-primary bg-sidebar-accent text-white'
                  : 'text-gray-400 hover:text-white hover:bg-sidebar-accent'
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Logout */}
      <div className="p-2 border-t border-sidebar-border">
        <form action={logoutAction}>
          <button
            type="submit"
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-sidebar-accent transition-colors"
          >
            <LogOut className="h-4 w-4 shrink-0" />
            <span>Logout</span>
          </button>
        </form>
      </div>
    </aside>
  )
}
