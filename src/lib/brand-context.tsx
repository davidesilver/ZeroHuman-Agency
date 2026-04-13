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

  useEffect(() => {
    async function loadBrands() {
      try {
        const resp = await fetch('/api/brands')
        const json = await resp.json()
        if (json.success && json.data.length > 0) {
          setBrands(json.data)
          // Restore from localStorage or use first
          const savedId = typeof window !== 'undefined' ? localStorage.getItem('activeBrandId') : null
          const saved = json.data.find((b: Brand) => b.id === savedId)
          setActiveBrandState(saved || json.data[0])
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
