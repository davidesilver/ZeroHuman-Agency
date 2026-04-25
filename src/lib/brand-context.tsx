'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'

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

const ACTIVE_BRAND_KEY = 'activeBrandId'
const BRANDS_CACHE_KEY = 'brandsCache.v1'
// Brand membership rarely changes; 5-minute SWR window is plenty and avoids
// hammering /api/brands on every page navigation.
const BRANDS_CACHE_TTL_MS = 5 * 60 * 1000

interface CachedBrands {
  brands: Brand[]
  ts: number
}

function readCache(): CachedBrands | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(BRANDS_CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as CachedBrands
    if (!parsed?.brands || !Number.isFinite(parsed.ts)) return null
    return parsed
  } catch {
    return null
  }
}

function writeCache(brands: Brand[]) {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(
      BRANDS_CACHE_KEY,
      JSON.stringify({ brands, ts: Date.now() }),
    )
  } catch {
    // sessionStorage may be unavailable (private mode); cache is opportunistic.
  }
}

function syncCookie(brandId: string) {
  if (typeof document === 'undefined') return
  document.cookie = `active_brand_id=${brandId}; path=/; SameSite=Lax; max-age=31536000`
}

function pickInitial(brands: Brand[]): Brand | null {
  if (brands.length === 0) return null
  const savedId =
    typeof window !== 'undefined'
      ? window.localStorage.getItem(ACTIVE_BRAND_KEY)
      : null
  return brands.find((b) => b.id === savedId) ?? brands[0]
}

export function BrandProvider({ children }: { children: ReactNode }) {
  const [brands, setBrands] = useState<Brand[]>(() => readCache()?.brands ?? [])
  const [activeBrand, setActiveBrandState] = useState<Brand | null>(() =>
    pickInitial(readCache()?.brands ?? []),
  )
  const [isLoading, setIsLoading] = useState(() => {
    const cache = readCache()
    return !cache || cache.brands.length === 0
  })
  const fetchedRef = useRef(false)

  useEffect(() => {
    // Sync cookie immediately for SSR requests on this tab; the server cannot
    // see localStorage, so the cookie is the only thing that travels.
    if (activeBrand) syncCookie(activeBrand.id)
  }, [activeBrand])

  useEffect(() => {
    if (fetchedRef.current) return
    fetchedRef.current = true

    const cache = readCache()
    const cacheFresh =
      !!cache && Date.now() - cache.ts < BRANDS_CACHE_TTL_MS

    if (cacheFresh) {
      // Cache is hot — render with what we have and skip the network entirely.
      setIsLoading(false)
      return
    }

    let cancelled = false
    ;(async () => {
      try {
        const resp = await fetch('/api/brands')
        const json = await resp.json()
        if (cancelled) return
        if (json.success && Array.isArray(json.data) && json.data.length > 0) {
          const next: Brand[] = json.data
          writeCache(next)
          setBrands(next)
          // Preserve current active brand if it's still in the list,
          // otherwise reseed from localStorage / first item.
          const stillValid =
            activeBrand && next.some((b) => b.id === activeBrand.id)
          const initial = stillValid ? activeBrand : pickInitial(next)
          setActiveBrandState(initial)
          if (initial) syncCookie(initial.id)
        }
      } catch {
        // Network failure: keep whatever was hydrated from cache.
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
    // Run once per provider mount; we explicitly do NOT depend on activeBrand
    // (the ref guard makes this safe and avoids re-entrancy).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const setActiveBrand = useCallback((brand: Brand) => {
    setActiveBrandState(brand)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(ACTIVE_BRAND_KEY, brand.id)
    }
    syncCookie(brand.id)
  }, [])

  return (
    <BrandContext.Provider
      value={{ brands, activeBrand, setActiveBrand, isLoading }}
    >
      {children}
    </BrandContext.Provider>
  )
}

export function useBrand() {
  return useContext(BrandContext)
}
