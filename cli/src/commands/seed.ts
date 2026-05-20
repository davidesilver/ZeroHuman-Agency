import { spawnSync } from 'child_process'
import { existsSync } from 'fs'
import { join } from 'path'
import { printSection, ok, fail, info } from '../lib/logo.js'

export async function runSeed(opts: { force?: boolean } = {}): Promise<void> {
  printSection('Seed Agent System')

  const seedScript = join(process.cwd(), 'python', 'scripts', 'seed_agent_system.py')
  if (!existsSync(seedScript)) {
    fail(`Seed script not found: ${seedScript}`)
    process.exit(1)
  }

  const args = ['run', 'python', seedScript]
  if (opts.force) args.push('--force')

  info('Seeding agent configs, skills, and examples...')
  const result = spawnSync('uv', args, { stdio: 'inherit', cwd: join(process.cwd(), 'python') })

  if (result.status === 0) {
    ok('Agent system seeded successfully')
  } else {
    fail('Seed script failed — check the output above')
    info('Make sure uv is installed and SUPABASE credentials are in .env.local')
  }
}
