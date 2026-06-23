"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AMapLoader from "@amap/amap-jsapi-loader";
import { ExternalLink, MapPin } from "lucide-react";
import { getAmapJsKey, getAmapWebServiceKey } from "@/lib/amap-config";
import {
  buildStaticMapUrl,
  stopsToMapPoints,
  type MapPoint,
} from "@/lib/amap-static-map";
import {
  buildAmapMarkerUrl,
  type ItineraryLeg,
  type ItineraryStop,
} from "@/lib/recommend-types";

interface Props {
  stops: ItineraryStop[];
  legs: ItineraryLeg[];
  activeStopId: string | null;
  onStopSelect?: (poiId: string) => void;
  className?: string;
}

function AmapMapFallback({
  points,
  legs,
  message,
  jsKeyMissing = false,
}: {
  points: MapPoint[];
  legs: ItineraryLeg[];
  message?: string;
  jsKeyMissing?: boolean;
}) {
  const webServiceKey = getAmapWebServiceKey();
  const staticUrl =
    webServiceKey && points.length > 0
      ? buildStaticMapUrl(webServiceKey, points, legs, 640, 280)
      : null;

  return (
    <div
      className="rounded-xl overflow-hidden space-y-2"
      style={{ border: "1px solid var(--border)", background: "var(--bg-page)" }}
    >
      {staticUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={staticUrl} alt="行程路线静态地图" className="w-full h-[200px] object-cover" />
      ) : (
        <div
          className="h-[200px] flex flex-col items-center justify-center gap-2 px-4 text-center"
          style={{ color: "var(--text-muted)" }}
        >
          <MapPin className="w-8 h-8 opacity-40" />
          <p className="text-[12px] leading-relaxed">
            {message ??
              (jsKeyMissing
                ? "未配置 JS API Key，无法加载交互地图"
                : "地图加载失败")}
          </p>
          <p className="text-[10px] leading-relaxed">
            JS API：frontend/.env.local → NEXT_PUBLIC_AMAP_JS_KEY
            <br />
            静态图兜底：NEXT_PUBLIC_AMAP_WEB_SERVICE_KEY
          </p>
        </div>
      )}
      {points.length > 0 && (
        <div className="px-3 pb-3 flex flex-wrap gap-1.5">
          {points.map((pt) => (
            <a
              key={pt.poi_id}
              href={buildAmapMarkerUrl(pt.lng, pt.lat, pt.name)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-full transition-opacity hover:opacity-80"
              style={{
                background: "var(--accent-bg)",
                color: "var(--accent)",
                border: "1px solid var(--border-accent)",
              }}
            >
              {pt.name}
              <ExternalLink className="w-2.5 h-2.5" />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AmapMap({
  stops,
  legs,
  activeStopId,
  onStopSelect,
  className = "",
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<AMap.Map | null>(null);
  const amapRef = useRef<typeof AMap | null>(null);
  const markersRef = useRef<AMap.Marker[]>([]);
  const polylinesRef = useRef<AMap.Polyline[]>([]);
  const infoWindowRef = useRef<AMap.InfoWindow | null>(null);

  const [sdkReady, setSdkReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const jsKey = getAmapJsKey();
  const points = useMemo(() => stopsToMapPoints(stops), [stops]);
  const stopsKey = useMemo(
    () => stops.map((s) => `${s.poi_id}:${s.lng},${s.lat}`).join("|"),
    [stops]
  );
  const legsKey = useMemo(
    () =>
      legs
        .map((l) => `${l.from_poi_id}-${l.to_poi_id}:${l.path.length}:${l.estimated}`)
        .join("|"),
    [legs]
  );

  const clearOverlays = useCallback(() => {
    markersRef.current.forEach((marker) => marker.setMap(null));
    polylinesRef.current.forEach((line) => line.setMap(null));
    markersRef.current = [];
    polylinesRef.current = [];
  }, []);

  useEffect(() => {
    if (!jsKey || points.length === 0 || !containerRef.current) {
      setSdkReady(false);
      return;
    }

    let cancelled = false;
    setLoadError(null);
    setSdkReady(false);

    AMapLoader.load({
      key: jsKey,
      version: "2.0",
      plugins: ["AMap.Scale", "AMap.ToolBar"],
    })
      .then((AMap) => {
        if (cancelled || !containerRef.current) return;

        amapRef.current = AMap;
        const map = new AMap.Map(containerRef.current, {
          viewMode: "2D",
          zoom: 12,
          center: [points[0].lng, points[0].lat],
        });
        map.add(new AMap.Scale());
        map.add(new AMap.ToolBar({ position: { right: "12px", bottom: "12px" } }));

        mapRef.current = map;
        infoWindowRef.current = new AMap.InfoWindow({
          offset: new AMap.Pixel(0, -28),
        });
        setSdkReady(true);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : "高德地图 SDK 加载失败"
          );
        }
      });

    return () => {
      cancelled = true;
      clearOverlays();
      infoWindowRef.current = null;
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
      }
      amapRef.current = null;
      setSdkReady(false);
    };
  }, [jsKey, stopsKey, clearOverlays]);

  useEffect(() => {
    const map = mapRef.current;
    const AMap = amapRef.current;
    if (!sdkReady || !map || !AMap || points.length === 0) return;

    clearOverlays();

    points.forEach((pt, index) => {
      const marker = new AMap.Marker({
        position: [pt.lng, pt.lat],
        title: pt.name,
        label: {
          content: `<span style="font-size:11px;font-weight:600;color:#1677ff">${index + 1}</span>`,
          direction: "top",
        },
      });
      marker.on("click", () => onStopSelect?.(pt.poi_id));
      marker.setMap(map);
      markersRef.current.push(marker);
    });

    legs.forEach((leg) => {
      let path: [number, number][];
      if (leg.path.length >= 2) {
        path = leg.path.map(([lng, lat]) => [lng, lat] as [number, number]);
      } else {
        const from = points.find((p) => p.poi_id === leg.from_poi_id);
        const to = points.find((p) => p.poi_id === leg.to_poi_id);
        if (!from || !to) return;
        path = [
          [from.lng, from.lat],
          [to.lng, to.lat],
        ];
      }

      const line = new AMap.Polyline({
        path,
        strokeColor: "#1677ff",
        strokeWeight: 4,
        strokeOpacity: leg.estimated ? 0.55 : 0.9,
        strokeStyle: leg.estimated ? "dashed" : "solid",
      });
      line.setMap(map);
      polylinesRef.current.push(line);
    });

    if (points.length >= 2) {
      map.setFitView(
        [...markersRef.current, ...polylinesRef.current],
        false,
        [40, 40, 40, 40]
      );
    } else {
      map.setZoomAndCenter(14, [points[0].lng, points[0].lat]);
    }
  }, [sdkReady, points, legsKey, legs, clearOverlays, onStopSelect]);

  useEffect(() => {
    const map = mapRef.current;
    const infoWindow = infoWindowRef.current;
    if (!sdkReady || !map || !activeStopId) return;

    const pt = points.find((p) => p.poi_id === activeStopId);
    if (!pt) return;

    map.setZoomAndCenter(15, [pt.lng, pt.lat]);
    if (infoWindow) {
      infoWindow.setContent(
        `<div style="font-size:12px;padding:2px 4px;max-width:180px">${pt.name}</div>`
      );
      infoWindow.open(map, [pt.lng, pt.lat]);
    }
  }, [sdkReady, activeStopId, points]);

  if (points.length === 0) {
    return (
      <div
        className={`flex items-center justify-center rounded-xl text-[12px] ${className}`}
        style={{
          border: "1px solid var(--border)",
          background: "var(--bg-page)",
          color: "var(--text-muted)",
        }}
      >
        所选地点缺少坐标，无法展示地图
      </div>
    );
  }

  if (!jsKey) {
    return (
      <div className={className}>
        <AmapMapFallback
          points={points}
          legs={legs}
          jsKeyMissing
        />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className={className}>
        <AmapMapFallback points={points} legs={legs} message={loadError} />
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl overflow-hidden ${className}`}
      style={{ border: "1px solid var(--border)" }}
    >
      <div ref={containerRef} className="w-full h-full min-h-[200px]" />
    </div>
  );
}
