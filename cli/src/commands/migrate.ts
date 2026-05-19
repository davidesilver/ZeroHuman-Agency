import { execSync, spawnSync } from 'child_process'
import { existsSync, readdirSync } from 'fs'
import { join } from 'path'
import { printSection, ok, fail, info, warn } from '../lib/logo.js'
import { read as readEnv } from '../lib/env-writer.js'

export async function runMigrate(opts: { status?: boolean } = {}): Promise<void> {
  printSection(opts.status ? 'Migration Status' : 'Running Migrations')

  // Check for supabase CLI
  let hasSbCli = false
  try { execSync('supabase --version 2>&1', { timeout: 3000 }); hasSbCli = true } catch {}

  const migrationsDir = join(process.cwd(), 'supabase', 'migrations')
  const hasMigrationsDir = existsSync(migrationsDir)

  if (hasMigrationsDir) {
    const files = readdirSync(migrationsDir).filter(f => f.endsWith('.sql')).sort()
    info(`Found ${files.length} migration files`)
    if (opts.status) {
      for (const f of files.slice(-5)) console.log(`  · ${f}`)
      if (files.length > 5) console.log(`  ... and ${files.length - 5} more`)
      return
    }
  }

  if (opts.status) { info('Run zh migrate to apply pending migrations'); return }

  if (hasSbCli) {
    info('Running supabase db push...')
    const result = spawnSync('supabase', ['db', 'push'], { stdio: 'inherit', cwd: process.cwd() })
    if (result.status === 0) {
      ok('Migrations applied successfully')
    } else {
      fail('supabase db push failed — check your Supabase connection')
      info('Make sure you have run: supabase link --project-ref <ref>')
    }
    return
  }

  warn('Supabase CLI not installed')
  info('Install: npm install -g supabase  or  brew install supabase/tap/supabase')
  info('Then run: supabase link --project-ref <your-ref> && supabase db push')
}
