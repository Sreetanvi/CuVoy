import type { ItineraryDay, ItineraryItem, PlanResult } from "@cuvoy/contracts";

import { clockFromLocal, formatMinutes } from "@/lib/format";
import { isValidLngLat, validLineCoords } from "@/lib/geo";
import { geometryToLine } from "@/lib/polyline";

/** Day 1–6 muted earth tones, then cycle. */
export const DAY_ROUTE_COLORS = [
  "#1E3A8A",
  "#2D5A27",
  "#B45309",
  "#78350F",
  "#475569",
  "#0F766E",
] as const;

export const DEFAULT_ROUTE_COLOR = "#1E3A8A";

export type MapStop = {
  placeId: string;
  name: string;
  lat: number;
  lng: number;
  dayIndex: number;
  sequence: number;
  arrival: string;
  duration: string;
  item: ItineraryItem;
};

export type DayRouteFeature = {
  type: "Feature";
  properties: { color: string; day_index: number };
  geometry: { type: "LineString"; coordinates: [number, number][] };
};

export function dayRouteColor(dayIndex: number): string {
  const index = Number(dayIndex);
  if (!Number.isFinite(index)) {
    return DEFAULT_ROUTE_COLOR;
  }
  return DAY_ROUTE_COLORS[((index % DAY_ROUTE_COLORS.length) + DAY_ROUTE_COLORS.length) % DAY_ROUTE_COLORS.length];
}

function placeLngLat(item: ItineraryItem): [number, number] | null {
  const place = item.place;
  if (!place) {
    return null;
  }
  const lng = Number(place.lng);
  const lat = Number(place.lat);
  if (!isValidLngLat(lng, lat)) {
    return null;
  }
  return [lng, lat];
}

export function isRenderableStop(item: ItineraryItem): boolean {
  if (placeLngLat(item) == null) {
    return false;
  }
  // Number from this filtered list only — never day.items index (that skips Marker 1).
  return item.type === "activity";
}

export function renderableStops(day: ItineraryDay): ItineraryItem[] {
  const visits: ItineraryItem[] = [];
  for (const item of day.items) {
    if (isRenderableStop(item)) {
      visits.push(item);
    }
  }
  return visits;
}

export function visitStopsForDays(
  days: ItineraryDay[],
  options: { continuous?: boolean } = {},
): MapStop[] {
  const stops: MapStop[] = [];
  let continuous = 0;
  for (const day of days) {
    renderableStops(day).forEach((item, index) => {
      const place = item.place!;
      const coords = placeLngLat(item)!;
      continuous += 1;
      stops.push({
        placeId: place.id,
        name: item.title || place.name,
        lat: coords[1],
        lng: coords[0],
        dayIndex: day.day_index,
        sequence: options.continuous ? continuous : index + 1,
        arrival: clockFromLocal(item.start),
        duration: formatMinutes(item.dwell_minutes) || `${clockFromLocal(item.start)}–${clockFromLocal(item.end)}`,
        item,
      });
    });
  }
  return stops;
}

export function sequenceByPlaceId(stops: MapStop[]): Map<string, number> {
  const map = new Map<string, number>();
  for (const stop of stops) {
    if (!map.has(stop.placeId)) {
      map.set(stop.placeId, stop.sequence);
    }
  }
  return map;
}

export function visibleDays(result: PlanResult, selectedDayIndex: number, showFullTrip: boolean): ItineraryDay[] {
  const days = result.itinerary.days;
  if (showFullTrip) {
    return days;
  }
  const wanted = Number(selectedDayIndex);
  const matched = days.filter((day) => Number(day.day_index) === wanted);
  if (matched.length) {
    return matched;
  }
  return days[0] ? [days[0]] : [];
}

function samePoint(a: [number, number], b: [number, number]): boolean {
  return a[0] === b[0] && a[1] === b[1];
}

function unclose(line: [number, number][]): [number, number][] {
  const coordinates = [...line];
  if (coordinates.length >= 2 && samePoint(coordinates[0], coordinates[coordinates.length - 1])) {
    coordinates.pop();
  }
  return coordinates;
}

/** Open LineString of visit stops [0..N]. Never closes back to coords[0]. */
export function openStopLine(stops: MapStop[]): [number, number][] {
  const coordinates: [number, number][] = [];
  for (const stop of stops) {
    const point: [number, number] = [stop.lng, stop.lat];
    const last = coordinates[coordinates.length - 1];
    if (!last || !samePoint(last, point)) {
      coordinates.push(point);
    }
  }
  return unclose(coordinates);
}

function roadLineForDay(dayStops: MapStop[], day: ItineraryDay | undefined): [number, number][] {
  const fallback = openStopLine(dayStops);
  if (!day) {
    return fallback;
  }
  const combined: [number, number][] = [];
  const seen = new Set<string>();
  for (const item of day.items) {
    const geometry = item.route?.geometry;
    if (!geometry || seen.has(geometry)) {
      continue;
    }
    seen.add(geometry);
    const line = unclose(validLineCoords(geometryToLine(geometry)));
    if (line.length < 2) {
      continue;
    }
    for (const point of line) {
      const last = combined[combined.length - 1];
      if (!last || !samePoint(last, point)) {
        combined.push(point);
      }
    }
  }
  if (combined.length >= 2) {
    return unclose(combined);
  }
  return fallback;
}

export function routeFeaturesFromStops(stops: MapStop[], days: ItineraryDay[]): DayRouteFeature[] {
  const allowedDays = new Set(days.map((day) => Number(day.day_index)));
  const byDay = new Map<number, ItineraryDay>();
  for (const day of days) {
    byDay.set(Number(day.day_index), day);
  }
  const grouped = new Map<number, MapStop[]>();
  for (const stop of stops) {
    const dayIndex = Number(stop.dayIndex);
    if (allowedDays.size && !allowedDays.has(dayIndex)) {
      continue;
    }
    const list = grouped.get(dayIndex) ?? [];
    list.push(stop);
    grouped.set(dayIndex, list);
  }
  const features: DayRouteFeature[] = [];
  const emitted = new Set<number>();
  for (const [dayIndex, dayStops] of grouped) {
    const coordinates = roadLineForDay(dayStops, byDay.get(dayIndex));
    if (coordinates.length < 2) {
      continue;
    }
    emitted.add(dayIndex);
    features.push({
      type: "Feature",
      properties: { color: dayRouteColor(dayIndex), day_index: dayIndex },
      geometry: { type: "LineString", coordinates },
    });
  }
  for (const day of days) {
    const dayIndex = Number(day.day_index);
    if (emitted.has(dayIndex)) {
      continue;
    }
    const coordinates = roadLineForDay([], day);
    if (coordinates.length < 2) {
      continue;
    }
    features.push({
      type: "Feature",
      properties: { color: dayRouteColor(dayIndex), day_index: dayIndex },
      geometry: { type: "LineString", coordinates },
    });
  }
  return features;
}

export function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
