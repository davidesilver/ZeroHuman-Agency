import { spawn } from 'child_process'
import chalk from 'chalk'
import { printSection, ok, fail, info } from '../lib/logo.js'
import { read as readEnv } from '../lib/env-writer.js'
import { checkBackend } from '../lib/health.js'

interface StartOptions { docker?: boolean; apiOnly?: boolean; webOnly?: boolean }

export async function runStart(opts: StartOptions = {}): Promise<void> {
  printSection('Starting ZeroHuman Agency')

  if (opts.docker) {
    info('Starting via Docker Compose...')
    const proc = spawn('docker', ['compose', '-f', 'docker-compose.full.yaml', 'up'], {
      stdio: 'inherit',
      cwd: process.cwd(),
    })
    proc.on('close', code => {
      if (code === 0) ok('Services started')
      else fail(`Docker exited with code ${code}`)
    })
    return
  }

  const env = readEnv()
  if (!env.NEXT_PUBLIC_SUPABASE_URL) {
    fail('Not configured — run zh init first')
    process.exit(1)
  }

  if (!opts.apiOnly) info('Starting Next.js frontend...')
  if (!opts.webOnly) info('Starting Python backend...')
  console.log()
  info('Run npm run dev in the project root to start all services')
  info('Or: npm run dev:next (frontend) / npm run dev:api (backend)')
}
