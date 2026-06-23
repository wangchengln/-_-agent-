import type { ItineraryLeg, ItineraryStop } from "@/lib/recommend-types";

export interface MapPoint {
  poi_id: string;
  name: string;
  lng: number;
  lat: number;
}

export function stopsToMapPoints(stops: ItineraryStop[]): MapPoint[] {
  return stops
    .filter((s) => s.lng != null && s.lat != null)
    .map((s) => ({
      poi_id: s.poi_id,
      name: s.name,
      lng: s.lng as number,
      lat: s.lat as number,
    }));
}

/** Build Amap static map URL (Tier B fallback when JS SDK unavailable). */
export function buildStaticMapUrl(
  apiKey: string,
  points: MapPoint[],
  legs: ItineraryLeg[],
  width = 640,
  height = 320,
): string {
  if (points.length === 0) return "";

  const center = points[0];
  const params = new URLSearchParams({
    key: apiKey,
    location: `${center.lng},${center.lat}`,
    zoom: points.length === 1 ? "14" : "12",
    size: `${width}*${height}`,
    scale: "2",
  });

  const markerParts = points.map(
    (p, i) => `mid,0x1677ff,${i + 1}:${p.lng},${p.lat}`
  );
  params.set("markers", markerParts.join("|"));

  const pathSegments: string[] = [];
  for (const leg of legs) {
    const path = leg.path.filter((pt) => pt.length === 2);
    if (path.length >= 2) {
      pathSegments.push(
        `2,0x1677ff,0.8,,:${path.map(([lng, lat]) => `${lng},${lat}`).join(";")}`
      );
    }
  }
  if (pathSegments.length === 0 && points.length >= 2) {
    pathSegments.push(
      `2,0x1677ff,0.8,,:${points.map((p) => `${p.lng},${p.lat}`).join(";")}`
    );
  }
  if (pathSegments.length > 0) {
    params.set("paths", pathSegments.join("|"));
  }

  return `https://restapi.amap.com/v3/staticmap?${params.toString()}`;
}
