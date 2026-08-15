/** Mapbox Directions `geometries=polyline` (precision 5) → [lng, lat] pairs. */
export function decodePolyline(encoded: string): [number, number][] {
  const coordinates: [number, number][] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let result = 0;
    let shift = 0;
    let byte: number;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lat += result & 1 ? ~(result >> 1) : result >> 1;

    result = 0;
    shift = 0;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lng += result & 1 ? ~(result >> 1) : result >> 1;

    coordinates.push([lng / 1e5, lat / 1e5]);
  }

  return coordinates;
}

export function geometryToLine(geometry: string): [number, number][] {
  const trimmed = geometry.trim();
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      const parsed = JSON.parse(trimmed) as {
        coordinates?: [number, number][];
        geometry?: { coordinates?: [number, number][] };
      };
      return parsed.coordinates ?? parsed.geometry?.coordinates ?? [];
    } catch {
      return [];
    }
  }
  return decodePolyline(trimmed);
}
