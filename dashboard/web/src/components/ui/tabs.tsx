import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

export const Tabs = TabsPrimitive.Root;
export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...p }, ref) => (
  <TabsPrimitive.List ref={ref} className={cn("flex w-full border-b border-[#2f3336]", className)} {...p} />
));
TabsList.displayName = "TabsList";

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, children, ...p }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "relative flex-1 h-[53px] text-[15px] capitalize text-[#71767b] transition-colors",
      "hover:bg-[#181818] focus-visible:outline-none focus-visible:bg-[#181818]",
      "data-[state=active]:text-[#e7e9ea] data-[state=active]:font-bold",
      "after:absolute after:bottom-0 after:left-1/2 after:-translate-x-1/2 after:h-1 after:w-14",
      "after:rounded-full after:bg-transparent data-[state=active]:after:bg-[#1d9bf0]",
      className
    )}
    {...p}
  >
    {children}
  </TabsPrimitive.Trigger>
));
TabsTrigger.displayName = "TabsTrigger";
export const TabsContent = TabsPrimitive.Content;
