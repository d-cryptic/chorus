import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

export const Tabs = TabsPrimitive.Root;
export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...p }, ref) => (
  <TabsPrimitive.List ref={ref} className={cn("flex w-full border-b border-[var(--border)]", className)} {...p} />
));
TabsList.displayName = "TabsList";

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, children, ...p }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "relative flex-1 h-[52px] text-[13.5px] capitalize transition-colors",
      "text-[var(--muted-foreground)] hover:text-[var(--muted-foreground)] hover:bg-[var(--card)]",
      "focus-visible:outline-none focus-visible:bg-[var(--card)]",
      "data-[state=active]:text-[var(--foreground)] data-[state=active]:font-semibold",
      "after:absolute after:bottom-[-1px] after:left-1/2 after:-translate-x-1/2 after:h-[2px] after:w-8",
      "after:rounded-full after:bg-transparent after:transition-all",
      "data-[state=active]:after:bg-[var(--primary)] data-[state=active]:after:w-10",
      className
    )}
    {...p}
  >
    {children}
  </TabsPrimitive.Trigger>
));
TabsTrigger.displayName = "TabsTrigger";
export const TabsContent = TabsPrimitive.Content;
