"use client"

import { Tabs as TabsPrimitive } from "@base-ui/react/tabs"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/**
 * Tabs — Light-mode pill-toggle + line variants.
 *
 * Default (pill-toggle):
 *  - List: surface-2 (warm-white) + hairline border — creates warm container
 *  - Tab active: surface-1 (white) + warm shadow — pops out of warm container
 *
 * Line variant:
 *  - List: hairline bottom border
 *  - Tab active: ink text + 2px coral bottom border
 */
function Tabs({
  className,
  orientation = "horizontal",
  ...props
}: TabsPrimitive.Root.Props) {
  return (
    <TabsPrimitive.Root
      data-slot="tabs"
      data-orientation={orientation}
      className={cn(
        "group/tabs flex gap-2 data-horizontal:flex-col",
        className
      )}
      {...props}
    />
  )
}

const tabsListVariants = cva(
  cn(
    "group/tabs-list inline-flex w-fit items-center justify-center",
    "text-ink-subtle",
    "group-data-horizontal/tabs:h-9",
    "group-data-vertical/tabs:h-fit group-data-vertical/tabs:flex-col"
  ),
  {
    variants: {
      variant: {
        // Pill-toggle: warm-white container + hairline — active tab (white) pops out
        default: "bg-[var(--surface-2)] border border-hairline rounded-md p-1 gap-1",
        // Linear bottom-line pattern
        line: "border-b border-hairline gap-4 rounded-none",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function TabsList({
  className,
  variant = "default",
  ...props
}: TabsPrimitive.List.Props & VariantProps<typeof tabsListVariants>) {
  return (
    <TabsPrimitive.List
      data-slot="tabs-list"
      data-variant={variant}
      className={cn(tabsListVariants({ variant }), className)}
      {...props}
    />
  )
}

function TabsTrigger({ className, ...props }: TabsPrimitive.Tab.Props) {
  return (
    <TabsPrimitive.Tab
      data-slot="tabs-trigger"
      className={cn(
        // Base
        "relative inline-flex items-center justify-center gap-1.5",
        "px-3 py-1 text-sm font-medium whitespace-nowrap",
        "transition-colors outline-none",
        "disabled:pointer-events-none disabled:opacity-50",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0",
        "[&_svg:not([class*='size-'])]:size-4",
        // Default variant (pill-toggle, Linear pricing-tab spec)
        "group-data-[variant=default]/tabs-list:rounded-md",
        "group-data-[variant=default]/tabs-list:h-7",
        "group-data-[variant=default]/tabs-list:text-ink-subtle",
        "group-data-[variant=default]/tabs-list:hover:text-ink",
        // Active tab: white (surface-1) pops out of warm container
        "group-data-[variant=default]/tabs-list:data-active:bg-[var(--surface-1)]",
        "group-data-[variant=default]/tabs-list:data-active:text-ink",
        "group-data-[variant=default]/tabs-list:data-active:[box-shadow:var(--shadow-sm)]",
        // Line variant (bottom-bordered tabs)
        "group-data-[variant=line]/tabs-list:rounded-none",
        "group-data-[variant=line]/tabs-list:px-1",
        "group-data-[variant=line]/tabs-list:py-2",
        "group-data-[variant=line]/tabs-list:text-ink-muted",
        "group-data-[variant=line]/tabs-list:hover:text-ink",
        "group-data-[variant=line]/tabs-list:data-active:text-ink",
        // Line variant: 2px coral bottom border on active (Linear active state)
        "group-data-[variant=line]/tabs-list:after:absolute",
        "group-data-[variant=line]/tabs-list:after:inset-x-0",
        "group-data-[variant=line]/tabs-list:after:-bottom-px",
        "group-data-[variant=line]/tabs-list:after:h-0.5",
        "group-data-[variant=line]/tabs-list:after:bg-[var(--brand-primary)]",
        "group-data-[variant=line]/tabs-list:after:opacity-0",
        "group-data-[variant=line]/tabs-list:after:transition-opacity",
        "group-data-[variant=line]/tabs-list:data-active:after:opacity-100",
        // Focus
        "focus-visible:outline-2 focus-visible:outline-[var(--brand-primary-focus)]/50 focus-visible:outline-offset-1",
        className
      )}
      {...props}
    />
  )
}

function TabsContent({ className, ...props }: TabsPrimitive.Panel.Props) {
  return (
    <TabsPrimitive.Panel
      data-slot="tabs-content"
      className={cn("flex-1 text-sm outline-none", className)}
      {...props}
    />
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent, tabsListVariants }
