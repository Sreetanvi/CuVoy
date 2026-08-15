const MULTI_CITIES =
  /^((?:[A-Za-z][\w.'-]*(?:\s+[A-Za-z][\w.'-]*){0,3}\s*,\s*){1,}[A-Za-z][\w.'-]*(?:\s+[A-Za-z][\w.'-]*){0,3})/;

const PLACE_AFTER_PREPOSITION =
  /\b(?:in|to|around|near|visiting|visit)\s+([A-Za-z][\w.'-]*(?:\s+[A-Za-z][\w.'-]*){0,3})/i;

const LEADING_PLACE = /^([A-Za-z][\w.'-]*(?:\s+[A-Za-z][\w.'-]*){0,3})\s*[,:—-]/;

function cleanPlace(raw: string): string {
  return raw
    .replace(/[.,;:!?]+$/g, "")
    .replace(/\b(for|and|with|from)\b.*$/i, "")
    .trim();
}

export function extractDestinationFromPrompt(prompt: string): string | null {
  const text = prompt.trim();
  if (!text) {
    return null;
  }

  const multi = text.match(MULTI_CITIES);
  if (multi?.[1]) {
    const place = multi[1].replace(/\s+for\s+\d+\s+days?.*$/i, "").trim();
    if (place.includes(",")) {
      return place;
    }
  }

  const afterPrep = text.match(PLACE_AFTER_PREPOSITION);
  if (afterPrep?.[1]) {
    const place = cleanPlace(afterPrep[1]);
    if (place.length >= 2) {
      return place;
    }
  }

  const leading = text.match(LEADING_PLACE);
  if (leading?.[1]) {
    const place = cleanPlace(leading[1]);
    if (place.length >= 2) {
      return place;
    }
  }

  if (/^[A-Za-z][\w.'-]*(?:\s+[A-Za-z][\w.'-]*){0,3}$/.test(text)) {
    return text;
  }

  return null;
}

export function resolveLocationQuery(destination: string, prompt: string): string | null {
  const explicit = destination.trim();
  if (explicit) {
    return explicit;
  }
  return extractDestinationFromPrompt(prompt);
}
