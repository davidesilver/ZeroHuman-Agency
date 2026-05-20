import chalk from 'chalk'
import { printSection, ok, fail } from '../lib/logo.js'
import { read as readEnv, set as setEnv, envPath, maskSecret, isSecretKey } from '../lib/env-writer.js'

export async function runConfigGet(key: string): Promise<void> {
  const env = readEnv()
  const val = env[key]
  if (!val) { fail(`Key not found: ${key}`); process.exit(1) }
  const display = isSecretKey(key) ? maskSecret(val) : val
  console.log(display)
}

export async function runConfigSet(key: string, value: string): Promise<void> {
  setEnv(key, value)
  ok(`${key} updated in .env.local`)
}

export async function runConfigList(): Promise<void> {
  printSection('Configuration')
  const env = readEnv()
  if (!Object.keys(env).length) {
    fail('.env.local not found or empty — run zh init')
    return
  }
  for (const [k, v] of Object.entries(env)) {
    const display = isSecretKey(k) ? chalk.hex('#555')(maskSecret(v)) : chalk.hex('#f5f0e8')(v)
    console.log(`  ${chalk.hex('#888')(k.padEnd(40))} ${display}`)
  }
  console.log()
}

export async function runConfigPath(): Promise<void> {
  console.log(envPath())
}
