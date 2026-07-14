import * as React from "react";
import { cn } from "@/lib/utils";
export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...p }, ref) =>
  <div ref={ref} className={cn("rounded-lg border bg-card text-card-foreground", className)} {...p} />);
Card.displayName = "Card";
export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...p }, ref) =>
  <div ref={ref} className={cn("p-4", className)} {...p} />);
CardContent.displayName = "CardContent";
