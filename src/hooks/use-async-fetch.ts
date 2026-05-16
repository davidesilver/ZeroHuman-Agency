'use client'

import { useCallback, useEffect, useState } from 'react'

interface UseAsyncFetchResult<T> {
  data: T | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Wraps fetch with loading/error/data state. Retries once on network failure.
 */
export function useAsyncFetch<T = unknown>(
  url: string | null,
  options?: RequestInit
): UseAsyncFetchResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    if (!url) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(url, options)
      if (!res.ok) {
        setError(`Request failed (${res.status})`)
        setLoading(false)
        return
      }
      setData(await res.json())
    } catch (firstError) {
      // Retry once on network error
      try {
        const res = await fetch(url, options)
        if (!res.ok) {
          setError(`Request failed (${res.status})`)
          setLoading(false)
          return
        }
        setData(await res.json())
      } catch {
        setError(firstError instanceof Error ? firstError.message : 'Network error')
      }
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { data, loading, error, refetch: fetchData }
}
