"use client";

import { useLayoutEffect, useRef } from "react";

import { cn } from "@/lib/utils";

type Props = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  minRows?: number;
  maxRows?: number;
};

export function AutosizeTextarea({
  className,
  minRows = 2,
  maxRows = 10,
  value,
  onChange,
  ...props
}: Props) {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) {
      return;
    }
    const styles = window.getComputedStyle(node);
    const lineHeight = Number.parseFloat(styles.lineHeight) || 20;
    const padding =
      Number.parseFloat(styles.paddingTop) + Number.parseFloat(styles.paddingBottom);
    const minHeight = lineHeight * minRows + padding;
    const maxHeight = lineHeight * maxRows + padding;
    node.style.height = "auto";
    const next = Math.min(Math.max(node.scrollHeight, minHeight), maxHeight);
    node.style.height = `${next}px`;
    node.style.overflowY = node.scrollHeight > maxHeight ? "auto" : "hidden";
  }, [maxRows, minRows, value]);

  return (
    <textarea
      {...props}
      ref={ref}
      value={value}
      onChange={onChange}
      rows={minRows}
      className={cn("resize-none overflow-hidden", className)}
    />
  );
}
