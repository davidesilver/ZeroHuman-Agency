import * as p from '@clack/prompts'
import chalk from 'chalk'
import { printSection, ok, fail, info } from '../lib/logo.js'
import { read as readEnv } from '../lib/env-writer.js'

async function getBackendUrl(): Promise<string> {
  const env = readEnv()
  return env.PYTHON_BACKEND_URL ?? 'http://localhost:8082'
}

export async function runBrandCreate(): Promise<void> {
  printSection('Create Brand')

  const name = await p.text({ message: 'Brand name', placeholder: 'Acme Corp' })
  if (p.isCancel(name)) { process.exit(0) }

  const autoSlug = (name as string).toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '')
  const slug = await p.text({
    message: 'Slug (immutable after creation)',
    placeholder: autoSlug,
    initialValue: autoSlug,
  })
  if (p.isCancel(slug)) { process.exit(0) }

  const topics = await p.text({
    message: 'Topics (comma-separated, optional)',
    placeholder: 'SaaS, marketing, growth',
  })

  const budget = await p.text({
    message: 'Daily budget USD (optional, leave blank for unlimited)',
    placeholder: '5.00',
  })

  info(`Creating brand "${name as string}"...`)

  try {
    const backendUrl = await getBackendUrl()
    const topicsArr = (topics as string)?.split(',').map((t: string) => t.trim()).filter(Boolean) ?? []
    const res = await fetch(`${backendUrl}/brands`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: (name as string).trim(),
        slug: (slug as string).trim(),
        topics: topicsArr,
        daily_budget_usd: budget ? parseFloat(budget as string) : null,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({})) as { detail?: string }
      fail(`Failed to create brand: ${err.detail ?? res.statusText}`)
      process.exit(1)
    }
    const data = await res.json() as { id?: string; brand_id?: string }
    const id = data.id ?? data.brand_id
    ok(`Brand created: ${name as string} (${slug as string}) — id: ${id}`)
  } catch (err: unknown) {
    fail(`Network error: ${String(err)}`)
    info('Make sure the backend is running: npm run dev:api')
    process.exit(1)
  }
}

export async function runBrandList(): Promise<void> {
  printSection('Brands')
  try {
    const backendUrl = await getBackendUrl()
    const res = await fetch(`${backendUrl}/brands`, { signal: AbortSignal.timeout(5000) })
    if (!res.ok) { fail(`Backend returned ${res.status}`); process.exit(1) }
    const data = await res.json() as Array<{ id: string; name: string; slug: string }>
    if (!data.length) {
      info('No brands found — run zh brand create')
      return
    }
    for (const brand of data) {
      console.log(`  ${chalk.hex('#f5f0e8')(brand.name.padEnd(28))} ${chalk.hex('#555')(brand.slug.padEnd(20))} ${chalk.hex('#444')(brand.id)}`)
    }
    console.log()
  } catch (err: unknown) {
    fail(`Could not reach backend: ${String(err)}`)
    info('Start it with: npm run dev:api')
  }
}
