import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useAsyncFetch } from './use-async-fetch'

const mockFetch = vi.fn()
global.fetch = mockFetch

describe('useAsyncFetch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('handles null url by setting loading to false', async () => {
    const { result } = renderHook(() => useAsyncFetch(null))

    expect(result.current.loading).toBe(false)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('fetches data successfully on first try', async () => {
    const mockData = { id: 1, name: 'Test' }
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const { result } = renderHook(() => useAsyncFetch('/api/test'))

    // Initial state
    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toEqual(mockData)
    expect(result.current.error).toBeNull()
    expect(mockFetch).toHaveBeenCalledTimes(1)
    expect(mockFetch).toHaveBeenCalledWith('/api/test', undefined)
  })

  it('handles fetch failure (non-200 status)', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
    })

    const { result } = renderHook(() => useAsyncFetch('/api/test'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Request failed (404)')
    expect(result.current.data).toBeNull()
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })

  it('retries once on network error and succeeds', async () => {
    const mockData = { id: 2, name: 'Test 2' }

    // First try throws a network error
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    // Second try succeeds
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const { result } = renderHook(() => useAsyncFetch('/api/test'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toEqual(mockData)
    expect(result.current.error).toBeNull()
    expect(mockFetch).toHaveBeenCalledTimes(2)
  })

  it('retries once on network error and fails again with network error', async () => {
    // Both tries throw network error
    mockFetch.mockRejectedValueOnce(new Error('First network error'))
    mockFetch.mockRejectedValueOnce(new Error('Second network error'))

    const { result } = renderHook(() => useAsyncFetch('/api/test'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('First network error')
    expect(result.current.data).toBeNull()
    expect(mockFetch).toHaveBeenCalledTimes(2)
  })

  it('retries once on network error and gets non-200 status on retry', async () => {
    // First try throws network error
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    // Second try gets 500
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    })

    const { result } = renderHook(() => useAsyncFetch('/api/test'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Request failed (500)')
    expect(result.current.data).toBeNull()
    expect(mockFetch).toHaveBeenCalledTimes(2)
  })

  it('handles refetch manually', async () => {
    const mockData1 = { id: 1 }
    const mockData2 = { id: 2 }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData1),
    })

    const { result } = renderHook(() => useAsyncFetch('/api/test'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toEqual(mockData1)

    // Setup for refetch
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData2),
    })

    act(() => {
      result.current.refetch()
    })

    // Expect loading state again
    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toEqual(mockData2)
    expect(mockFetch).toHaveBeenCalledTimes(2)
  })
})
