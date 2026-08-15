"use client";

import type { WarningCode } from "@cuvoy/contracts";

const COPY: Record<WarningCode, string> = {
  closes_before_arrival: "May close before arrival",
  reservation_likely: "Reservation likely needed",
  hours_unverified: "Hours unverified",
  cost_unavailable: "Cost unavailable",
};

export function Warnings({ codes }: { codes: WarningCode[] }) {
  if (codes.length === 0) {
    return null;
  }
  return (
    <ul className="mt-1 space-y-0.5 text-xs text-accent-brown">
      {codes.map((code) => (
        <li key={code}>{COPY[code]}</li>
      ))}
    </ul>
  );
}
