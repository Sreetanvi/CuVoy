/**
 * Itinerary times already include IANA `timezone` and `local_time`.
 * Never convert unless the user explicitly asks (PROJECT_SPEC §7 / contracts).
 */
export function displayLocalTime(localTime: string, timezone: string): string {
  return `${localTime} (${timezone})`;
}

export function displayLocalTimeOnly(localTime: string): string {
  return localTime;
}

/** Display the clock portion of an already-local timestamp. Does not convert zones. */
export function clockPortion(localTime: string): string {
  if (localTime.includes("T")) {
    return (localTime.split("T")[1] ?? localTime).slice(0, 5);
  }
  return localTime.slice(0, 5);
}
