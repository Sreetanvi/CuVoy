"use client";

import { Separator } from "react-resizable-panels";

import { cn } from "@/lib/utils";

export function ResizeHandle({
  direction,
  className,
}: {
  direction: "horizontal" | "vertical";
  className?: string;
}) {
  return (
    <Separator
      className={cn(
        "group relative shrink-0 bg-transparent outline-none",
        direction === "horizontal" ? "w-1.5 cursor-col-resize" : "h-1.5 cursor-row-resize",
        className,
      )}
      aria-label={
        direction === "horizontal"
          ? "Resize map and itinerary"
          : "Resize planner and trip controls"
      }
    >
      <span
        className={cn(
          "absolute bg-border transition-colors group-hover:bg-accent-green group-focus-visible:bg-accent-green group-active:bg-accent-green",
          direction === "horizontal"
            ? "inset-y-0 left-1/2 w-px -translate-x-1/2"
            : "inset-x-0 top-1/2 h-px -translate-y-1/2",
        )}
      />
      <span
        className={cn(
          "absolute rounded-sm bg-border opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100 group-active:bg-accent-green group-active:opacity-100",
          direction === "horizontal"
            ? "top-1/2 left-1/2 h-8 w-1 -translate-x-1/2 -translate-y-1/2"
            : "top-1/2 left-1/2 h-1 w-8 -translate-x-1/2 -translate-y-1/2",
        )}
      />
    </Separator>
  );
}
