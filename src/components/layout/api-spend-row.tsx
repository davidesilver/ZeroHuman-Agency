import Link from 'next/link'

export function APISpendRow() {
  return (
    <div className="h-8 bg-brand-secondary/10 flex items-center justify-between px-4 rounded-md">
      <span className="text-sm text-muted-foreground">
        API spend today: $0.00 &mdash; threshold $5.00
      </span>
      <Link
        href="/costi-api"
        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        Details &rarr;
      </Link>
    </div>
  )
}
