import type { ExclusionReason, PlanResult } from "@cuvoy/contracts";

const OSM_ID = /^(osm:)?(node|way|relation)\//i;
const GENERIC = new Set([
  "",
  "unnamed place",
  "unnamed location",
  "unknown place",
  "nearby poi",
  "poi",
  "yes",
  "general",
]);

export function looksLikeRawPlaceId(value: string | null | undefined): boolean {
  if (!value) {
    return true;
  }
  const trimmed = value.trim();
  return OSM_ID.test(trimmed) || trimmed.startsWith("osm:");
}

function usable(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  const lowered = trimmed.toLowerCase();
  if (
    !trimmed ||
    GENERIC.has(lowered) ||
    lowered.startsWith("unnamed location") ||
    looksLikeRawPlaceId(trimmed)
  ) {
    return null;
  }
  return trimmed;
}

function titleize(value: string): string {
  return value.replaceAll("_", " ").trim().replace(/\b\w/g, (char) => char.toUpperCase());
}

function unnamed(placeId: string | null | undefined): string {
  return placeId ? `Unnamed Location (${placeId})` : "Unnamed Location";
}

export function exclusionDisplayName(exclusion: ExclusionReason, result: PlanResult): string {
  const direct = usable(exclusion.name);
  if (direct) {
    return direct;
  }
  const extra = exclusion as ExclusionReason & { category?: string | null; tags?: Record<string, string> };
  const tags = extra.tags;
  const fromTags = usable(tags?.name) || usable(tags?.["name:en"]) || usable(tags?.amenity) || usable(tags?.tourism);
  if (fromTags) {
    return titleize(fromTags);
  }
  const match = result.itinerary.days
    .flatMap((day) => day.items)
    .find((item) => item.place?.id === exclusion.place_id);
  const fromPlace = usable(match?.place?.name) || usable(match?.title);
  if (fromPlace) {
    return fromPlace;
  }
  if (usable(extra.category)) {
    return titleize(extra.category as string);
  }
  return unnamed(exclusion.place_id);
}
