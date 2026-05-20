#!/usr/bin/env node
/**
 * zh — ZeroHuman Agency CLI
 *
 * Usage:
 *   zh init          Full interactive setup
 *   zh doctor        Diagnose system health
 *   zh start         Start all services
 *   zh providers     Manage LLM providers
 *   zh brand         Manage brands
 *   zh mcp           Manage MCP connections
 *   zh config        Read/write configuration
 *   zh migrate       Run Supabase migrations
 *   zh seed          Seed agent system
 *   zh update        Update ZeroHuman
 *   zh reset         Factory reset
 *   zh status        Full system status
 */

import { program } from 'commander'
import { createRequire } from 'module'

const VERSION = '0.1.0'

program
  .name('zh')
  .description('ZeroHuman Agency CLI')
  .version(VERSION)

// ── zh init ───────────────────────────────────────────────────────────────────
program
  .command('init')
  .description('Full interactive setup — from zero to running stack')
  .option('--supabase-url <url>', 'Supabase project URL')
  .option('--supabase-anon-key <key>', 'Supabase anon key')
  .option('--supabase-service-key <key>', 'Supabase service role key')
  .option('--anthropic-key <key>', 'Anthropic API key')
  .option('--openrouter-key <key>', 'OpenRouter API key')
  .option('--serper-key <key>', 'Serper API key')
  .option('--resend-key <key>', 'Resend API key')
  .option('--no-migrations', 'Skip database migrations')
  .option('-y, --yes', 'Accept all defaults (non-interactive)')
  .action(async (opts) => {
    const { runInit } = await import('./commands/init.js')
    await runInit({
      supabaseUrl: opts.supabaseUrl,
      supabaseAnonKey: opts.supabaseAnonKey,
      supabaseServiceKey: opts.supabaseServiceKey,
      anthropicKey: opts.anthropicKey,
      openrouterKey: opts.openrouterKey,
      serperKey: opts.serperKey,
      resendKey: opts.resendKey,
      noMigrations: opts.noMigrations,
      yes: opts.yes,
    })
  })

// ── zh doctor ─────────────────────────────────────────────────────────────────
program
  .command('doctor')
  .description('Diagnose system health and configuration')
  .action(async () => {
    const { runDoctor } = await import('./commands/doctor.js')
    await runDoctor()
  })

// ── zh start ──────────────────────────────────────────────────────────────────
program
  .command('start')
  .description('Start all services (Next.js + Python backend)')
  .option('--docker', 'Use Docker Compose')
  .option('--api-only', 'Start only the Python backend')
  .option('--web-only', 'Start only the Next.js frontend')
  .action(async (opts) => {
    const { runStart } = await import('./commands/start.js')
    await runStart(opts)
  })

// ── zh providers ──────────────────────────────────────────────────────────────
const providers = program.command('providers').description('Manage LLM providers')

providers
  .command('list')
  .description('List all catalog providers with configured status')
  .action(async () => {
    const { runProvidersList } = await import('./commands/providers.js')
    await runProvidersList()
  })

providers
  .command('add [provider-id]')
  .description('Add or configure a provider API key')
  .action(async (id) => {
    const { runProvidersAdd } = await import('./commands/providers.js')
    await runProvidersAdd(id)
  })

providers
  .command('test <provider-id>')
  .description('Test an existing provider key')
  .action(async (id) => {
    const { runProvidersTest } = await import('./commands/providers.js')
    await runProvidersTest(id)
  })

providers
  .command('remove <provider-id>')
  .description('Remove a provider key from configuration')
  .action(async (id) => {
    const { runProvidersRemove } = await import('./commands/providers.js')
    await runProvidersRemove(id)
  })

// ── zh brand ──────────────────────────────────────────────────────────────────
const brand = program.command('brand').description('Manage brands')

brand
  .command('create')
  .description('Create a new brand interactively')
  .action(async () => {
    const { runBrandCreate } = await import('./commands/brand.js')
    await runBrandCreate()
  })

brand
  .command('list')
  .description('List all brands')
  .action(async () => {
    const { runBrandList } = await import('./commands/brand.js')
    await runBrandList()
  })

// ── zh mcp ────────────────────────────────────────────────────────────────────
const mcp = program.command('mcp').description('Manage MCP connections')

mcp
  .command('list')
  .description('List known MCP servers with connection status')
  .action(async () => {
    const { runMcpList } = await import('./commands/mcp.js')
    await runMcpList()
  })

mcp
  .command('add <server-id>')
  .description('Configure an MCP server')
  .action(async (id) => {
    const { runMcpAdd } = await import('./commands/mcp.js')
    await runMcpAdd(id)
  })

// ── zh config ─────────────────────────────────────────────────────────────────
const config = program.command('config').description('Read/write configuration')

config
  .command('get <key>')
  .description('Get a configuration value')
  .action(async (key) => {
    const { runConfigGet } = await import('./commands/config.js')
    await runConfigGet(key)
  })

config
  .command('set <key> <value>')
  .description('Set a configuration value')
  .action(async (key, value) => {
    const { runConfigSet } = await import('./commands/config.js')
    await runConfigSet(key, value)
  })

config
  .command('list')
  .description('List all configuration values (secrets masked)')
  .action(async () => {
    const { runConfigList } = await import('./commands/config.js')
    await runConfigList()
  })

config
  .command('path')
  .description('Print path to .env.local')
  .action(async () => {
    const { runConfigPath } = await import('./commands/config.js')
    await runConfigPath()
  })

// ── zh migrate ────────────────────────────────────────────────────────────────
program
  .command('migrate')
  .description('Run pending Supabase migrations')
  .option('--status', 'Show migration status without running')
  .action(async (opts) => {
    const { runMigrate } = await import('./commands/migrate.js')
    await runMigrate(opts)
  })

// ── zh seed ───────────────────────────────────────────────────────────────────
program
  .command('seed')
  .description('Seed agent configs, skills, and examples')
  .option('--force', 'Re-seed even if data exists')
  .action(async (opts) => {
    const { runSeed } = await import('./commands/seed.js')
    await runSeed(opts)
  })

// ── zh update ─────────────────────────────────────────────────────────────────
program
  .command('update')
  .description('Update ZeroHuman: pull, install, build, migrate')
  .option('--check', 'Check for updates without applying')
  .action(async (opts) => {
    const { runUpdate } = await import('./commands/update.js')
    await runUpdate(opts)
  })

// ── zh reset ──────────────────────────────────────────────────────────────────
program
  .command('reset')
  .description('Remove .env.local (factory reset)')
  .option('--hard', 'Also drop all database tables (DANGEROUS)')
  .action(async (opts) => {
    const { runReset } = await import('./commands/reset.js')
    await runReset(opts)
  })

// ── zh status ─────────────────────────────────────────────────────────────────
program
  .command('status')
  .description('Full system status overview')
  .action(async () => {
    const { runStatus } = await import('./commands/status.js')
    await runStatus()
  })

program.parse()
