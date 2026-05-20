import { spawnSync, execSync } from 'child_process'
import chalk from 'chalk'
import { printSection, ok, fail, info, warn } from '../lib/logo.js'
import { runMigrate } from './migrate.js'

export async function runUpdate(opts: { check?: boolean } = {}): Promise<void> {
  printSection(opts.check ? 'Checking for Updates' : 'Updating ZeroHuman Agency')

  if (opts.check) {
    try {
      execSync('git fetch origin main --quiet', { timeout: 10000 })
      const behind = execSync('git rev-list HEAD..origin/main --count').toString().trim()
      const commits = parseInt(behind, 10)
      if (commits === 0) {
        ok('Already up to date')
      } else {
        info(`${commits} commit(s) behind origin/main — run zh update to apply`)
      }
    } catch {
      warn('Could not check for updates — ensure git remote is configured')
    }
    return
  }

  // 1. git pull
  info('Pulling latest changes...')
  const pull = spawnSync('git', ['pull', 'origin', 'main', '--ff-only'], { stdio: 'inherit' })
  if (pull.status !== 0) { fail('git pull failed — resolve conflicts manually'); process.exit(1) }
  ok('Code updated')

  // 2. npm install
  info('Installing Node dependencies...')
  const npm = spawnSync('npm', ['install'], { stdio: 'inherit' })
  if (npm.status !== 0) { fail('npm install failed'); process.exit(1) }
  ok('Node dependencies updated')

  // 3. uv sync
  info('Syncing Python dependencies...')
  const uv = spawnSync('uv', ['sync'], { stdio: 'inherit', cwd: 'python' })
  if (uv.status !== 0) { warn('uv sync failed — Python deps may be stale') }
  else ok('Python dependencies updated')

  // 4. migrate
  info('Running migrations...')
  await runMigrate()

  console.log()
  ok(chalk.hex('#f5f0e8').bold('Update complete'))
}
