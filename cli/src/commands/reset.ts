import { unlinkSync, existsSync } from 'fs'
import * as p from '@clack/prompts'
import { printSection, ok, fail, info, warn } from '../lib/logo.js'
import { envPath } from '../lib/env-writer.js'

export async function runReset(opts: { hard?: boolean } = {}): Promise<void> {
  printSection('Factory Reset')

  if (opts.hard) {
    warn('--hard will DROP ALL DATABASE TABLES. This cannot be undone.')
    const confirm = await p.text({ message: 'Type RESET to confirm', placeholder: 'RESET' })
    if (p.isCancel(confirm) || confirm !== 'RESET') {
      info('Reset cancelled')
      process.exit(0)
    }
    warn('Hard reset not fully implemented — manually truncate tables via Supabase dashboard')
    return
  }

  const confirmReset = await p.confirm({ message: 'Remove .env.local? (You will need to run zh init again)' })
  if (!confirmReset || p.isCancel(confirmReset)) { info('Reset cancelled'); process.exit(0) }

  const p2 = envPath()
  if (existsSync(p2)) {
    unlinkSync(p2)
    ok('.env.local removed')
    info('Run zh init to reconfigure')
  } else {
    info('.env.local not found — nothing to remove')
  }
}
