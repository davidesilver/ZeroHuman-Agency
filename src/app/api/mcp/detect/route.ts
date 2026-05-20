/**
 * GET /api/mcp/detect
 *
 * Probes for running MCP servers by:
 * 1. Reading the Claude Desktop config file (if present)
 * 2. Checking known HTTP-based services that commonly run as MCP servers
 *
 * Returns an array of { id, label, status, capabilities?, configUrl? }
 */

import { requireAuth } from '@/lib/supabase/auth-helpers'
import { jsonResponse } from '@/lib/api-helpers'
import { readFile } from 'fs/promises'
import { homedir } from 'os'
import { join } from 'path'

interface McpServer {
  id: string
  label: string
  status: 'detected' | 'not_running'
  capabilities?: number
  configUrl?: string
}

// Known MCP servers — each entry describes how to detect it.
const KNOWN_SERVERS = [
  {
    id: 'supabase',
    label: 'Supabase MCP',
    configKey: 'supabase',
    httpProbe: 'http://localhost:54321/rest/v1/',
    configUrl: 'https://github.com/supabase-community/supabase-mcp',
  },
  {
    id: 'github',
    label: 'GitHub MCP',
    configKey: 'github',
    configUrl: 'https://github.com/github/github-mcp-server',
  },
  {
    id: 'linear',
    label: 'Linear MCP',
    configKey: 'linear',
    configUrl: 'https://github.com/modelcontextprotocol/servers/tree/main/src/linear',
  },
  {
    id: 'slack',
    label: 'Slack MCP',
    configKey: 'slack',
    configUrl: 'https://github.com/modelcontextprotocol/servers/tree/main/src/slack',
  },
  {
    id: 'filesystem',
    label: 'Filesystem MCP',
    configKey: 'filesystem',
    configUrl: 'https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem',
  },
  {
    id: 'puppeteer',
    label: 'Puppeteer MCP',
    configKey: 'puppeteer',
    configUrl: 'https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer',
  },
  {
    id: 'postgres',
    label: 'PostgreSQL MCP',
    configKey: 'postgres',
    configUrl: 'https://github.com/modelcontextprotocol/servers/tree/main/src/postgres',
  },
]

/** Paths where Claude Desktop stores its config, in priority order. */
function claudeConfigPaths(): string[] {
  const home = homedir()
  return [
    join(home, 'Library', 'Application Support', 'Claude', 'claude_desktop_config.json'),  // macOS
    join(home, '.config', 'claude', 'claude_desktop_config.json'),                          // Linux
    join(home, 'AppData', 'Roaming', 'Claude', 'claude_desktop_config.json'),              // Windows
  ]
}

async function readClaudeConfig(): Promise<Record<string, unknown>> {
  for (const path of claudeConfigPaths()) {
    try {
      const raw = await readFile(path, 'utf-8')
      const parsed = JSON.parse(raw)
      return parsed?.mcpServers ?? {}
    } catch {
      // Try next path
    }
  }
  return {}
}

async function probeHttp(url: string): Promise<boolean> {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(1500) })
    return res.ok || res.status < 500
  } catch {
    return false
  }
}

export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  // Read Claude Desktop config to find configured MCP servers
  const configured = await readClaudeConfig()
  const configuredKeys = new Set(Object.keys(configured))

  const results: McpServer[] = []

  await Promise.all(
    KNOWN_SERVERS.map(async (def) => {
      const inConfig = configuredKeys.has(def.configKey)
      let status: 'detected' | 'not_running' = 'not_running'

      if (inConfig) {
        status = 'detected'
      } else if (def.httpProbe) {
        // For HTTP-accessible services, probe even if not in config
        const alive = await probeHttp(def.httpProbe)
        if (alive) status = 'detected'
      }

      results.push({
        id: def.id,
        label: def.label,
        status,
        configUrl: def.configUrl,
      })
    })
  )

  // Sort: detected first, then alphabetically
  results.sort((a, b) => {
    if (a.status === b.status) return a.label.localeCompare(b.label)
    return a.status === 'detected' ? -1 : 1
  })

  return jsonResponse(results)
}
