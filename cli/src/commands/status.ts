import { printLogo, printSection } from '../lib/logo.js'
import { runDoctor } from './doctor.js'

export async function runStatus(): Promise<void> {
  // status = logo + doctor
  await runDoctor()
}
