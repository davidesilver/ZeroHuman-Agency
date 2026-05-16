/**
 * Shared status → Badge variant mapping for async job pages.
 * Used by deep-research, competitor-watch, videos, and automations.
 */
export const STATUS_BADGE_VARIANT: Record<string, string> = {
  pending: 'secondary',
  running: 'default',
  rendering: 'default',
  completed: 'outline',
  failed: 'destructive',
  active: 'default',
  inactive: 'secondary',
}

/**
 * Returns the badge variant for a given status string.
 * Falls back to 'secondary' for unknown statuses.
 */
export function getStatusVariant(status: string): string {
  return STATUS_BADGE_VARIANT[status] ?? 'secondary'
}
