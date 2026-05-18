/**
 * StagingBar — Coral signature strip at the top of every page.
 *
 * Uses the brand-primary (Coral) as a deliberate brand moment.
 * Linear has no equivalent — this is ZeroHuman's signature.
 * Typography: Linear eyebrow (uppercase, +0.15em tracking).
 */
export function StagingBar() {
  return (
    <div
      className="h-7 flex items-center justify-center"
      style={{ background: 'var(--staging-bg)' }}
    >
      <span
        className="text-[10px] font-bold uppercase"
        style={{
          color: 'var(--staging-text)',
          letterSpacing: '0.2em',
        }}
      >
        staging · zerohuman content engine
      </span>
    </div>
  )
}
