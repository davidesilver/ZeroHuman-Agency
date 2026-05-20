import chalk from 'chalk'
import * as p from '@clack/prompts'
import { printSection, ok, fail, info } from '../lib/logo.js'
import { checkUrl } from '../lib/health.js'
import { read as readEnv, write as writeEnv } from '../lib/env-writer.js'

const KNOWN_SERVERS = [
  { id: 'context7', label: 'Context7', urlKey: 'CONTEXT7_MCP_URL', defaultUrl: 'https://mcp.context7.com/mcp', requiresKey: false },
  { id: 'figma', label: 'Figma MCP', urlKey: '', defaultUrl: '', requiresKey: true, keyEnv: 'FIGMA_API_KEY', installUrl: 'https://www.figma.com/developers/api' },
  { id: 'supabase', label: 'Supabase MCP', urlKey: 'SUPABASE_MCP_URL', defaultUrl: '', requiresKey: false },
  { id: 'postiz', label: 'Postiz MCP', urlKey: 'POSTIZ_MCP_URL', defaultUrl: 'http://localhost:3100', requiresKey: false },
  { id: 'desktop-commander', label: 'Desktop Commander', urlKey: '', defaultUrl: '', requiresKey: false, notes: 'Install via Claude Code MCP settings' },
  { id: 'playwright', label: 'Playwright MCP', urlKey: '', defaultUrl: '', requiresKey: false, notes: 'Install: npx @playwright/mcp' },
]

export async function runMcpList(): Promise<void> {
  printSection('MCP Servers')
  const env = readEnv()

  const probes = await Promise.all(
    KNOWN_SERVERS.map(async (server) => {
      const url = env[server.urlKey ?? ''] ?? server.defaultUrl
      if (!url) return { ...server, status: 'skip' as const, detail: server.notes ?? 'URL not configured' }
      const result = await checkUrl(`${url}/health`, 2000).catch(() => ({ ok: false, latency_ms: 0 }))
      return {
        ...server,
        status: result.ok ? 'ok' as const : 'skip' as const,
        detail: result.ok ? `online (${result.latency_ms}ms)` : 'not reachable',
      }
    })
  )

  for (const s of probes) {
    const icon = s.status === 'ok' ? chalk.hex('#4ade80')('✓') : chalk.hex('#555')('○')
    const detail = s.status === 'ok' ? chalk.hex('#888')(s.detail) : chalk.hex('#444')(s.detail)
    console.log(`  ${icon}  ${chalk.hex('#f5f0e8')(s.label.padEnd(22))} ${detail}`)
  }
  console.log()
  info('Configure MCP servers in Settings → MCP Connections on the dashboard')
}

export async function runMcpAdd(id: string): Promise<void> {
  const server = KNOWN_SERVERS.find(s => s.id === id)
  if (!server) { fail(`Unknown MCP server: ${id}`); process.exit(1) }

  printSection(`Configure ${server.label}`)

  if (server.requiresKey && server.keyEnv) {
    const key = await p.text({ message: `${server.label} API key` })
    if (p.isCancel(key)) { process.exit(0) }
    writeEnv({ [server.keyEnv]: key as string })
    ok(`${server.label} configured`)
    return
  }

  if (server.urlKey) {
    const env = readEnv()
    const url = await p.text({
      message: `${server.label} URL`,
      placeholder: server.defaultUrl || 'http://localhost:...',
      initialValue: env[server.urlKey] ?? server.defaultUrl,
    })
    if (p.isCancel(url)) { process.exit(0) }
    writeEnv({ [server.urlKey]: url as string })
    ok(`${server.label} URL saved`)
  }

  if (server.notes) {
    info(server.notes)
  }
}
