'use client'

import { useBrand } from '@/lib/brand-context'

export function BrandSwitcher() {
  const { brands, activeBrand, setActiveBrand } = useBrand()

  if (brands.length <= 1) return null

  return (
    <div className="px-4 py-2">
      <select
        value={activeBrand?.id || ''}
        onChange={(e) => {
          const brand = brands.find(b => b.id === e.target.value)
          if (brand) setActiveBrand(brand)
        }}
        className="w-full bg-sidebar-accent text-white text-sm rounded-md px-2 py-1.5 border border-sidebar-border"
      >
        {brands.map(b => (
          <option key={b.id} value={b.id}>{b.name}</option>
        ))}
      </select>
    </div>
  )
}
