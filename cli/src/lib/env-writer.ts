/**
 * Atomic .env.local reader/writer.
 * Reads existing values, merges new ones, writes via temp-file rename.
 */

import { existsSync, readFileSync, writeFileSync, renameSync } from 'fs'
import { resolve, join } from 'path'

/** Resolve .env.local path from the repo root (cli/ is one level below root). */
export function envPath(): string {
  return resolve(__dirname, '..', '..', '..', '.env.local')
}

export function read(): Record<string, string> {
  const p = envPath()
  if (!existsSync(p)) return {}
  const content = readFileSync(p, 'utf-8')
  const result: Record<string, string> = {}
  for (const line of content.split('\n')) {
    const t = line.trim()
    if (!t || t.startsWith('#')) continue
    const idx = t.indexOf('=')
    if (idx === -1) continue
    result[t.slice(0, idx).trim()] = t.slice(idx + 1).trim()
  }
  return result
}

export function write(updates: Record<string, string>): void {
  const existing = read()
  const merged = { ...existing, ...updates }
  const content = Object.entries(merged)
    .map(([k, v]) => `${k}=${v}`)
    .join('\n') + '\n'
  const p = envPath()
  const tmp = p + '.tmp'
  writeFileSync(tmp, content, 'utf-8')
  renameSync(tmp, p)
}

export function get(key: string): string | undefined {
  return read()[key]
}

export function set(key: string, value: string): void {
  write({ [key]: value })
}

export function maskSecret(value: string): string {
  if (!value) return '(empty)'
  if (value.length <= 8) return '***'
  return value.slice(0, 4) + '…' + value.slice(-4)
}

export function isSecretKey(key: string): boolean {
  const lower = key.toLowerCase()
  return ['api_key', 'secret', 'token', 'password', 'service_role', 'private'].some(m => lower.includes(m))
}
