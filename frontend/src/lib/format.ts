import type { LocalDateTime } from "@cuvoy/contracts";

import { displayLocalTimeOnly } from "@/lib/timezone";

export function clockFromLocal(value: LocalDateTime): string {
  const raw = displayLocalTimeOnly(value.local_time);
  if (raw.includes("T")) {
    return (raw.split("T")[1] ?? raw).slice(0, 5);
  }
  return raw.slice(0, 5);
}

export function formatMinutes(minutes: number | null | undefined): string {
  if (minutes == null) {
    return "";
  }
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

export function formatCost(
  cost: { amount?: number | null; currency: string } | null | undefined,
): string {
  if (!cost || cost.amount == null) {
    return "";
  }
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: cost.currency,
      maximumFractionDigits: 0,
    }).format(cost.amount);
  } catch {
    return `${cost.currency} ${cost.amount}`;
  }
}

export function formatBufferedTravel(seconds: number | null | undefined): string {
  if (seconds == null) {
    return "";
  }
  return formatMinutes(Math.round(seconds / 60));
}
