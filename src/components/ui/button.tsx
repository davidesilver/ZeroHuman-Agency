import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/**
 * Button — Linear button-primary spec, ZeroHuman recolor.
 *
 * Linear specs (replicated exactly):
 *  - All buttons: rounded-md (8px), never pill
 *  - Primary: coral fill + obsidian text (Linear: lavender → coral swap)
 *  - Secondary: surface-1 + ink text + hairline border
 *  - Tertiary: canvas + ink text (no border)
 *  - Type: 14px / 500 / tracking 0 (button cap spec)
 *  - Padding: 8px 14px (Linear compact spec)
 *  - Focus: 2px coral outline at 50% opacity (Linear pattern)
 *  - No box-shadow on dark — Linear principle
 */
const buttonVariants = cva(
  cn(
    // Base shape (Linear button spec)
    "group/button inline-flex shrink-0 items-center justify-center gap-1.5",
    "rounded-md border border-transparent bg-clip-padding",
    "text-sm font-medium whitespace-nowrap",
    "transition-colors duration-100",
    "outline-none select-none",
    // Focus ring (Linear: 2px brand outline at 50% opacity)
    "focus-visible:outline-2 focus-visible:outline-offset-2",
    // Active press (subtle, no transform on Linear — kept minimal)
    "active:not-aria-[haspopup]:translate-y-px",
    "disabled:pointer-events-none disabled:opacity-50",
    "aria-invalid:border-[var(--status-error)]",
    "[&_svg]:pointer-events-none [&_svg]:shrink-0",
    "[&_svg:not([class*='size-'])]:size-4"
  ),
  {
    variants: {
      variant: {
        // Primary — Coral fill, dark text (Linear button-primary recolor)
        default: cn(
          "bg-[var(--brand-primary)] text-[var(--canvas)]",
          "hover:bg-[var(--brand-primary-hover)]",
          "active:bg-[var(--brand-primary-focus)]",
          "focus-visible:outline-[var(--brand-primary)]"
        ),
        // Secondary — surface-1 + hairline border (Linear button-secondary)
        outline: cn(
          "bg-[var(--surface-1)] text-ink border-hairline",
          "hover:bg-[var(--surface-2)] hover:border-hairline-strong",
          "focus-visible:outline-[var(--brand-primary)]"
        ),
        // Surface-2 fill (used for selected tabs etc — Linear pricing-tab-selected)
        secondary: cn(
          "bg-[var(--surface-2)] text-ink",
          "hover:bg-[var(--surface-3)]"
        ),
        // Tertiary / ghost — no background, hover lifts to surface-1
        ghost: cn(
          "text-ink-muted",
          "hover:bg-[var(--surface-1)] hover:text-ink",
          "aria-expanded:bg-[var(--surface-1)] aria-expanded:text-ink"
        ),
        // Destructive — soft red, no fill (subtle)
        destructive: cn(
          "bg-[var(--status-error)]/10 text-[var(--status-error)]",
          "hover:bg-[var(--status-error)]/20",
          "focus-visible:outline-[var(--status-error)]"
        ),
        // Link
        link: "text-[var(--brand-primary)] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-8 px-3 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        xs: "h-6 px-2 text-xs rounded-md gap-1 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 px-2.5 text-[13px] rounded-md gap-1 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-9 px-3.5 has-data-[icon=inline-end]:pr-2.5 has-data-[icon=inline-start]:pl-2.5",
        icon: "size-8",
        "icon-xs": "size-6 rounded-md [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-7 rounded-md [&_svg:not([class*='size-'])]:size-3.5",
        "icon-lg": "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
