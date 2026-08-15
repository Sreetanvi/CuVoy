"use client";

import { useState } from "react";

export function BrandLogo({ className = "h-8 w-8" }: { className?: string }) {
  const [src, setSrc] = useState("/logo.png");

  return (
    // Spec stores the circular convoy mark at public/logo.png. SVG is the local fallback.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt=""
      width={32}
      height={32}
      className={className}
      onError={() => setSrc("/logo.svg")}
    />
  );
}
