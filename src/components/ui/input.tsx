import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

/**
 * Input — Linear text-input spec.
 *
 * Linear spec:
 *  - Background: surface-1 (#0f1011)
 *  - Border: 1px hairline (#23252a)
 *  - Border-focus: hairline-strong (#34343a)
 *  - Rounded: md (8px)
 *  - Padding: 8px 12px
 *  - Type: body (16px / 400)
 *  - Focus: hairline strengthens, no glow ring (Linear uses 2px coral outline)
 */
function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        // Base shape
        "h-8 w-full min-w-0 rounded-md px-3 py-1",
        "text-sm transition-colors outline-none",
        // Surface (Linear text-input)
        "bg-[var(--surface-1)] text-ink",
        "border border-hairline",
        // Placeholder
        "placeholder:text-ink-tertiary",
        // Focus — hairline strengthens, coral outline
        "focus-visible:border-hairline-strong",
        "focus-visible:outline-2 focus-visible:outline-[var(--brand-primary-focus)]/50 focus-visible:outline-offset-1",
        // Disabled
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        // Invalid
        "aria-invalid:border-[var(--status-error)]",
        "aria-invalid:focus-visible:outline-[var(--status-error)]/50",
        // File
        "file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-ink",
        className
      )}
      style={{ letterSpacing: '-0.05px' }}
      {...props}
    />
  )
}

export { Input }
