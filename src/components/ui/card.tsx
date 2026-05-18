import * as React from "react"
import { cn } from "@/lib/utils"

/**
 * Card — Light-mode: white on cream canvas with Miro warm shadow.
 *
 * Default:
 *   - Background: surface-1 (white) on cream canvas
 *   - Border: 1px hairline (warm gray)
 *   - Rounded: 16px (Figma card radius)
 *   - Padding: 24px (lg)
 *   - Shadow: Miro warm purple-tinted shadow (replaces hairline-only)
 *
 * Variants:
 *   - default: white card with warm shadow
 *   - featured: surface-2 (warm-white) with stronger shadow
 *   - sm: tighter padding (16px)
 */

type CardVariant = "default" | "featured"
type CardSize = "default" | "sm"

function Card({
  className,
  variant = "default",
  size = "default",
  ...props
}: React.ComponentProps<"div"> & { variant?: CardVariant; size?: CardSize }) {
  return (
    <div
      data-slot="card"
      data-variant={variant}
      data-size={size}
      className={cn(
        "group/card flex flex-col gap-4 overflow-hidden",
        "text-sm text-card-foreground",
        "border border-hairline",
        // Figma card radius (16px)
        "rounded-[var(--radius-card)]",
        // surface
        variant === "featured" ? "bg-[var(--surface-2)]" : "bg-card",
        // Miro warm shadow — replaces hairline-only depth
        variant === "featured"
          ? "[box-shadow:var(--shadow-md)]"
          : "[box-shadow:var(--shadow-sm)]",
        // padding
        size === "sm" ? "p-4 gap-3" : "p-6 gap-4",
        className
      )}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "flex flex-col gap-1",
        className
      )}
      {...props}
    />
  )
}

function CardTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-title"
      className={cn(
        // Linear card-title spec: 22px / 500 / 1.25 / -0.4px
        "font-medium text-ink",
        className
      )}
      style={{
        fontSize: "18px",
        lineHeight: 1.25,
        letterSpacing: "-0.3px",
        ...((props.style ?? {}) as React.CSSProperties),
      }}
      {...props}
    />
  )
}

function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-description"
      className={cn(
        "text-sm text-ink-subtle",
        className
      )}
      {...props}
    />
  )
}

function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn("ml-auto", className)}
      {...props}
    />
  )
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-content"
      className={cn("flex-1", className)}
      {...props}
    />
  )
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn(
        "flex items-center pt-4 border-t border-hairline",
        className
      )}
      {...props}
    />
  )
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
}
