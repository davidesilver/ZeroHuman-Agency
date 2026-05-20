/**
 * Verified Knot ASCII logo for the zh CLI.
 *
 * The mark renders as two interlocking masses meeting through a central void —
 * obsidian background, ivory glyph, coral verification point.
 */

import chalk from 'chalk'

const MARK_LINES = [
  '  ██████  ██████  ',
  '  ██  ██  ██  ██  ',
  '  ██  ╔════╗  ██  ',
  '  ██  ║ ●  ║  ██  ',
  '  ██  ╚════╝  ██  ',
  '  ██  ██  ██  ██  ',
  '  ██████  ██████  ',
]

export function printLogo(version = '0.1.0'): void {
  const coral = chalk.hex('#FF6B6B')
  const ivory = chalk.hex('#f5f0e8')
  const dim = chalk.hex('#555555')

  // Replace ● with coral dot
  const lines = MARK_LINES.map(line =>
    ivory(line.replace('●', coral('●')))
  )

  console.log()
  console.log(lines[0])
  console.log(lines[1])
  console.log(lines[2])
  console.log(lines[3] + '  ' + ivory.bold('ZeroHuman Agency'))
  console.log(lines[4] + '  ' + dim(`v${version}`))
  console.log(lines[5])
  console.log(lines[6])
  console.log()
}

export function printSection(title: string): void {
  console.log(chalk.hex('#555555')('─'.repeat(44)))
  console.log(chalk.hex('#f5f0e8').bold(` ${title}`))
  console.log(chalk.hex('#555555')('─'.repeat(44)))
}

export function ok(msg: string): void {
  console.log(chalk.hex('#4ade80')('✓') + ' ' + msg)
}

export function fail(msg: string): void {
  console.log(chalk.hex('#f87171')('✗') + ' ' + msg)
}

export function warn(msg: string): void {
  console.log(chalk.hex('#facc15')('⚠') + ' ' + msg)
}

export function info(msg: string): void {
  console.log(chalk.hex('#60a5fa')('→') + ' ' + msg)
}
