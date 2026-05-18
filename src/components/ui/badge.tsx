import { mergeProps } from "@base-ui/react/merge-props"
import { useRender } from "@base-ui/react/use-render"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/**
 * Badge — Linear status-badge spec.
 *
 * Linear spec:
 *  - Background: surface-2 (#141516)
 *  - Text: ink-muted
 *  - Type: caption (12px / 400 / +0px tracking)
 *  - Rounded: pill (9999px) for status, xs (4px) for tags
 *  - Padding: 2px 8px
 *
 * Variants:
 *  - default: brand-primary (coral) — for active/important counts
 *  - secondary: surface-2 + ink-muted (Linear status-badge default)
 *  - outline: transparent + hairline border + ink
 *  - destructive: soft error
 */
const badgeVariants = cva(
  cn(
    "group/badge inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1",
    "overflow-hidden rounded px-2 py-0.5",
    "text-[11px] font-medium whitespace-nowrap",
    "transition-colors border border-transparent",
    "focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-1",
    "has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5",
    "[&>svg]:pointer-events-none [&>svg]:size-3"
  ),
  {
    variants: {
      variant: {
        default: cn(
          "bg-[var(--brand-primary)] text-[var(--canvas)]",
          "[a]:hover:bg-[var(--brand-primary-hover)]"
        ),
        secondary: cn(
          "bg-[var(--surface-2)] text-ink-muted",
          "[a]:hover:bg-[var(--surface-3)]"
        ),
        outline: cn(
          "bg-transparent border-hairline text-ink-muted",
          "[a]:hover:bg-[var(--surface-1)] [a]:hover:text-ink"
        ),
        destructive: cn(
          "bg-[var(--status-error)]/15 text-[var(--status-error)]"
        ),
        ghost: cn(
          "bg-transparent text-ink-subtle",
          "hover:bg-[var(--surface-1)] hover:text-ink"
        ),
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  render,
  ...props
}: useRender.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return useRender({
    defaultTagName: "span",
    props: mergeProps<"span">(
      {
        className: cn(badgeVariants({ variant }), className),
      },
      props
    ),
    render,
    state: {
      slot: "badge",
      variant,
    },
  })
}

export { Badge, badgeVariants }
