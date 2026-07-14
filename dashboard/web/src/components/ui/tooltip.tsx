import * as React from "react";
import * as T from "@radix-ui/react-tooltip";
import { cn } from "@/lib/utils";

export const TooltipProvider = T.Provider;
export const Tooltip = T.Root;
export const TooltipTrigger = T.Trigger;
export const TooltipContent = React.forwardRef<
  React.ElementRef<typeof T.Content>,
  React.ComponentPropsWithoutRef<typeof T.Content>
>(({ className, sideOffset = 6, ...p }, ref) => (
  <T.Portal>
    <T.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-50 rounded-md bg-[#16181c] border border-[#2f3336] px-2.5 py-1.5",
        "text-[12px] font-mono text-[#e7e9ea] shadow-xl data-[state=delayed-open]:animate-fade-in",
        className
      )}
      {...p}
    />
  </T.Portal>
));
TooltipContent.displayName = "TooltipContent";
