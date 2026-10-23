import { renderHook } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { usePolling } from './use-polling'

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('should call the callback immediately on mount', () => {
    const callback = vi.fn()
    renderHook(() => usePolling(callback, 1000))

    expect(callback).toHaveBeenCalledTimes(1)
  })

  it('should call the callback repeatedly at the given interval', () => {
    const callback = vi.fn()
    renderHook(() => usePolling(callback, 1000))

    expect(callback).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1000)
    expect(callback).toHaveBeenCalledTimes(2)

    vi.advanceTimersByTime(1000)
    expect(callback).toHaveBeenCalledTimes(3)
  })

  it('should use the latest callback if it changes', () => {
    const callback1 = vi.fn()
    const callback2 = vi.fn()
    const { rerender } = renderHook(
      ({ cb, interval }) => usePolling(cb, interval),
      { initialProps: { cb: callback1, interval: 1000 } }
    )

    expect(callback1).toHaveBeenCalledTimes(1)

    rerender({ cb: callback2, interval: 1000 })

    vi.advanceTimersByTime(1000)
    expect(callback1).toHaveBeenCalledTimes(1)
    expect(callback2).toHaveBeenCalledTimes(1)
  })

  it('should pause polling when document becomes hidden and resume when visible', () => {
    const callback = vi.fn()
    renderHook(() => usePolling(callback, 1000))

    expect(callback).toHaveBeenCalledTimes(1)

    // Simulate document becoming hidden
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true })
    document.dispatchEvent(new Event('visibilitychange'))

    vi.advanceTimersByTime(3000)
    expect(callback).toHaveBeenCalledTimes(1)

    // Simulate document becoming visible
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => false })
    document.dispatchEvent(new Event('visibilitychange'))

    // The start function calls tick() immediately when resuming
    expect(callback).toHaveBeenCalledTimes(2)

    vi.advanceTimersByTime(1000)
    expect(callback).toHaveBeenCalledTimes(3)
  })

  it('should stop polling when unmounted', () => {
    const callback = vi.fn()
    const { unmount } = renderHook(() => usePolling(callback, 1000))

    expect(callback).toHaveBeenCalledTimes(1)

    unmount()

    vi.advanceTimersByTime(3000)
    expect(callback).toHaveBeenCalledTimes(1)
  })
})
