export function isValidLngLat(lng: number, lat: number): boolean {
  return Number.isFinite(lng) && Number.isFinite(lat) && Math.abs(lng) <= 180 && Math.abs(lat) <= 90;
}

export function validLineCoords(coords: [number, number][]): [number, number][] {
  return coords.filter(([lng, lat]) => isValidLngLat(lng, lat));
}

export function validFitBounds(bounds: {
  min_lat: number;
  min_lng: number;
  max_lat: number;
  max_lng: number;
} | null | undefined): [[number, number], [number, number]] | null {
  if (!bounds) {
    return null;
  }
  const minLng = Number(bounds.min_lng);
  const minLat = Number(bounds.min_lat);
  const maxLng = Number(bounds.max_lng);
  const maxLat = Number(bounds.max_lat);
  if (!isValidLngLat(minLng, minLat) || !isValidLngLat(maxLng, maxLat)) {
    return null;
  }
  if (minLng === maxLng && minLat === maxLat) {
    return null;
  }
  return [
    [Math.min(minLng, maxLng), Math.min(minLat, maxLat)],
    [Math.max(minLng, maxLng), Math.max(minLat, maxLat)],
  ];
}
