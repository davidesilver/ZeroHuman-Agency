'use client'

import { useEffect, useRef } from 'react'

/**
 * Polls a callback at a fixed interval. Pauses when the tab is hidden.
 * Calls the callback immediately on mount and on every interval tick.
 */
export function usePolling(callback: () => void | Promise<void>, intervalMs: number) {
  const savedCallback = useRef(callback)

  useEffect(() => {
    savedCallback.current = callback
  }, [callback])

  useEffect(() => {
    let id: ReturnType<typeof setInterval> | null = null

    function tick() {
      savedCallback.current()
    }

    function start() {
      tick()
      id = setInterval(tick, intervalMs)
    }

    function stop() {
      if (id !== null) {
        clearInterval(id)
        id = null
      }
    }

    function handleVisibility() {
      if (document.hidden) {
        stop()
      } else {
        start()
      }
    }

    start()
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      stop()
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [intervalMs])
}
