'use client'

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'

interface Brand {
  id: string
  name: string
  slug: string
}

interface BrandContextType {
  brands: Brand[]
  activeBrand: Brand | null
  setActiveBrand: (brand: Brand) => void
  isLoading: boolean
}

const BrandContext = createContext<BrandContextType>({
  brands: [],
  activeBrand: null,
  setActiveBrand: () => {},
  isLoading: true,
})

export function BrandProvider({ children }: { children: ReactNode }) {
  const [brands, setBrands] = useState<Brand[]>([])
  const [activeBrand, setActiveBrandState] = useState<Brand | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  /** Write active_brand_id to cookie so server-side requireAuth() can read it. */
  function syncCookie(brandId: string) {
    if (typeof document === 'undefined') return
    document.cookie = `active_brand_id=${brandId}; path=/; SameSite=Lax; max-age=31536000`
  }

  useEffect(() => {
    async function loadBrands() {
      try {
        const resp = await fetch('/api/brands')
        const json = await resp.json()
        if (json.success && json.data.length > 0) {
          setBrands(json.data)
          // Restore from localStorage (persists across tabs) or cookie (synced with server),
          // then fall back to the first brand.
          const savedId =
            typeof window !== 'undefined'
              ? localStorage.getItem('activeBrandId')
              : null
          const saved = json.data.find((b: Brand) => b.id === savedId)
          const initial: Brand = saved || json.data[0]
          setActiveBrandState(initial)
          // Ensure cookie is in sync with the resolved initial brand.
          syncCookie(initial.id)
        }
      } catch {}
      setIsLoading(false)
    }
    loadBrands()
  }, [])

  const setActiveBrand = useCallback((brand: Brand) => {
    setActiveBrandState(brand)
    if (typeof window !== 'undefined') {
      localStorage.setItem('activeBrandId', brand.id)
    }
    syncCookie(brand.id)
  }, [])

  return (
    <BrandContext.Provider value={{ brands, activeBrand, setActiveBrand, isLoading }}>
      {children}
    </BrandContext.Provider>
  )
}

export function useBrand() {
  return useContext(BrandContext)
}
