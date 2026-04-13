'use client'

import { useEffect } from 'react'
import { createBrowserClient } from '@supabase/ssr'
import type { RealtimePostgresChangesPayload } from '@supabase/supabase-js'

const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

type TableName = 'research_items' | 'content_drafts' | 'research_runs' | 'newsletters' | 'api_costs'

/**
 * Subscribe to Supabase Realtime changes on a table.
 * Calls `onchange` whenever an INSERT, UPDATE, or DELETE occurs.
 */
export function useRealtime(
  table: TableName,
  onChange: (payload: RealtimePostgresChangesPayload<Record<string, unknown>>) => void,
  filter?: string
) {
  useEffect(() => {
    const channelName = `realtime-${table}-${filter || 'all'}`

    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes' as any,
        {
          event: '*',
          schema: 'public',
          table,
          ...(filter ? { filter } : {}),
        },
        (payload: RealtimePostgresChangesPayload<Record<string, unknown>>) => {
          onChange(payload)
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [table, filter, onChange])
}
