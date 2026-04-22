'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChevronDown, Plus, Check, Building } from 'lucide-react'
import { useBrand } from '@/lib/brand-context'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

/**
 * P1.6 — Brand switcher in sidebar.
 *
 * Always rendered so the user can see which brand is active and navigate to
 * settings to add a second one. Previously hidden when brands.length <= 1.
 *
 * On switch: updates BrandContext (→ localStorage + active_brand_id cookie),
 * then reloads so all server-side API calls pick up the new cookie value.
 */
export function BrandSwitcher() {
  const router = useRouter()
  const { brands, activeBrand, setActiveBrand, isLoading } = useBrand()
  const [open, setOpen] = useState(false)

  const handleSwitch = (brand: { id: string; name: string; slug: string }) => {
    if (brand.id === activeBrand?.id) return
    setActiveBrand(brand)
    setOpen(false)
    // Hard reload so all server-side API calls pick up the new active_brand_id cookie.
    window.location.reload()
  }

  const handleAddBrand = () => {
    setOpen(false)
    router.push('/settings')
  }

  if (isLoading) {
    return (
      <div className="mx-3 my-2 h-8 bg-sidebar-accent rounded animate-pulse" />
    )
  }

  return (
    <div className="px-3 pb-1">
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger
          className="w-full flex items-center gap-2 rounded-md px-2 py-1.5 text-sm
                     bg-sidebar-accent hover:bg-sidebar-accent/80 text-white
                     transition-colors text-left"
          title={activeBrand?.slug}
        >
          <Building className="size-3.5 shrink-0 opacity-70" />
          <span className="flex-1 truncate font-medium">
            {activeBrand?.name ?? 'Select brand'}
          </span>
          <ChevronDown className="size-3.5 shrink-0 opacity-60" />
        </DropdownMenuTrigger>

        <DropdownMenuContent side="right" align="start" className="w-52" sideOffset={8}>
          {brands.map((brand) => (
            <DropdownMenuItem
              key={brand.id}
              onClick={() => handleSwitch(brand)}
              className="flex items-center justify-between cursor-pointer"
            >
              <span className="truncate">{brand.name}</span>
              {brand.id === activeBrand?.id && (
                <Check className="size-3.5 shrink-0 text-brand-primary" />
              )}
            </DropdownMenuItem>
          ))}

          <DropdownMenuSeparator />

          <DropdownMenuItem
            onClick={handleAddBrand}
            className="flex items-center gap-2 cursor-pointer"
          >
            <Plus className="size-3.5" />
            <span>Add brand</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
