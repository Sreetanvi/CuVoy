import type { Itinerary, ItineraryItem } from "@cuvoy/contracts";

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

function escapeText(value: string): string {
  return value
    .replaceAll("\\", "\\\\")
    .replaceAll(";", "\\;")
    .replaceAll(",", "\\,")
    .replaceAll("\r\n", "\\n")
    .replaceAll("\n", "\\n");
}

function stamp(localTime: string, fallbackDate: string): string {
  const text = localTime.trim();
  let dateDigits = "";
  let timeDigits = "";
  if (text.includes("T")) {
    const [datePart, timePart = ""] = text.split("T");
    dateDigits = (datePart ?? "").replaceAll(/\D/g, "").slice(0, 8);
    timeDigits = timePart.split(/[+-]/)[0]?.replaceAll(/\D/g, "").slice(0, 6) ?? "";
  } else {
    const digits = text.replaceAll(/\D/g, "");
    if (digits.length >= 8) {
      dateDigits = digits.slice(0, 8);
      timeDigits = digits.slice(8, 14);
    } else {
      timeDigits = digits.slice(0, 6);
    }
  }
  if (dateDigits.length < 8) {
    dateDigits = fallbackDate.replaceAll(/\D/g, "").slice(0, 8);
  }
  return `${dateDigits.padEnd(8, "0").slice(0, 8)}T${timeDigits.padEnd(6, "0").slice(0, 6)}`;
}

function isStop(item: ItineraryItem): boolean {
  if ((item.type === "transit" || item.type === "break") && !item.place) {
    return false;
  }
  return item.type === "activity" || item.type === "meal" || item.type === "travel_day" || Boolean(item.place);
}

function utcStamp(): string {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}T${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}Z`;
}

export function itineraryToIcs(itinerary: Itinerary, planId: string): string {
  const zones = new Set<string>();
  if (itinerary.timezone) {
    zones.add(itinerary.timezone);
  }
  for (const day of itinerary.days) {
    zones.add(day.timezone || itinerary.timezone);
  }

  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//CuVoy//Travel Planner//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    `X-WR-TIMEZONE:${itinerary.timezone}`,
  ];

  for (const tzid of zones) {
    lines.push(
      "BEGIN:VTIMEZONE",
      `TZID:${tzid}`,
      `X-LIC-LOCATION:${tzid}`,
      "BEGIN:STANDARD",
      "DTSTART:19700101T000000",
      "TZOFFSETFROM:+0000",
      "TZOFFSETTO:+0000",
      `TZNAME:${tzid}`,
      "END:STANDARD",
      "END:VTIMEZONE",
    );
  }

  itinerary.days.forEach((day, dayIndex) => {
    const tzid = day.timezone || itinerary.timezone;
    const fallbackDate = day.date;
    day.items.forEach((item, itemIndex) => {
      if (!isStop(item)) {
        return;
      }
      const title = item.title || item.place?.name || "CuVoy stop";
      const start = stamp(item.start.local_time, fallbackDate);
      const end = stamp(item.end.local_time, fallbackDate);
      lines.push(
        "BEGIN:VEVENT",
        `UID:${planId}-${dayIndex}-${itemIndex}-${start}@cuvoy.app`,
        `DTSTAMP:${utcStamp()}`,
        `DTSTART;TZID=${tzid}:${start}`,
        `DTEND;TZID=${tzid}:${end}`,
        `SUMMARY:${escapeText(title)}`,
      );
      if (item.place) {
        lines.push(
          `LOCATION:${escapeText(`${item.place.name} (${item.place.lat.toFixed(5)}, ${item.place.lng.toFixed(5)})`)}`,
          `GEO:${item.place.lat.toFixed(6)};${item.place.lng.toFixed(6)}`,
        );
      }
      const notes = [item.reason, item.cost ? `Cost: ${item.cost.amount ?? ""} ${item.cost.currency}`.trim() : null]
        .filter(Boolean)
        .join(" ");
      if (notes) {
        lines.push(`DESCRIPTION:${escapeText(notes)}`);
      }
      lines.push("END:VEVENT");
    });
  });

  lines.push("END:VCALENDAR");
  return `${lines.join("\r\n")}\r\n`;
}

export function isValidIcs(text: string): boolean {
  return (
    text.includes("BEGIN:VCALENDAR") &&
    text.includes("END:VCALENDAR") &&
    text.includes("BEGIN:VEVENT") &&
    text.includes("TZID")
  );
}
