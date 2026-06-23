"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import AMapLoader from "@amap/amap-jsapi-loader";
import { ChevronDown, ChevronUp, MapPin } from "lucide-react";
import { getAmapJsKey, getAmapWebServiceKey } from "@/lib/amap-config";
import {
  buildFeedStaticMapUrl,
  feedItemsToMapPoints,
} from "@/lib/amap-static-map";
import type { FeedItem } from "@/lib/recommend-types";
import { buildAmapMarkerUrl } from "@/lib/recommend-types";

interface Props {
  items: FeedItem[];
  activePoiId: string | null;
  onPoiSelect?: (poiId: string) => void;
  className?: string;
}

export default function FeedMapOverview({
  items,
  activePoiId,
  onPoiSelect,
  className = "",
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<AMap.Map | null>(null);
  const markersRef = useRef<AMap.Marker[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const points = useMemo(() => feedItemsToMapPoints(items), [items]);
  const jsKey = getAmapJsKey();
  const webKey = getAmapWebServiceKey();
  const staticUrl =
    webKey && points.length > 0
      ? buildFeedStaticMapUrl(webKey, points, activePoiId, 640, 200)
      : null;

  useEffect(() => {
    if (!jsKey || collapsed || points.length === 0 || !containerRef.current) {
      return;
    }

    let cancelled = false;
    setLoadError(null);

    AMapLoader.load({
      key: jsKey,
      version: "2.0",
      plugins: ["AMap.Scale"],
    })
      .then((AMap) => {
        if (cancelled || !containerRef.current) return;

        if (mapRef.current) {
          mapRef.current.destroy();
          mapRef.current = null;
        }
        markersRef.current = [];

        const map = new AMap.Map(containerRef.current, {
          viewMode: "2D",
          zoom: 12,
          center: [points[0].lng, points[0].lat],
        });
        map.add(new AMap.Scale());

        const markers: AMap.Marker[] = [];
        points.forEach((pt) => {
          const isActive = pt.poi_id === activePoiId;
          const marker = new AMap.Marker({
            position: [pt.lng, pt.lat],
            title: pt.name,
            label: {
              content: `<span style="font-size:10px;padding:1px 4px;border-radius:4px;background:${
                isActive ? "#e67e22" : "#1677ff"
              };color:#fff;">${pt.name.slice(0, 6)}</span>`,
              direction: "top",
            },
          });
          marker.on("click", () => onPoiSelect?.(pt.poi_id));
          marker.setMap(map);
          markers.push(marker);
          markersRef.current.push(marker);
        });

        if (markers.length >= 2) {
          map.setFitView(markers, false, [24, 24, 24, 24]);
        }

        mapRef.current = map;
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "地图加载失败");
        }
      });

    return () => {
      cancelled = true;
      markersRef.current = [];
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
      }
    };
  }, [jsKey, collapsed, points, activePoiId, onPoiSelect]);

  if (points.length === 0) return null;

  const activePoint = points.find((p) => p.poi_id === activePoiId) ?? points[0];

  return (
    <div
      className={`rounded-xl overflow-hidden ${className}`}
      style={{ border: "1px solid var(--border)", background: "var(--bg-page)" }}
    >
      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-[11px] font-medium transition-opacity hover:opacity-80"
        style={{ color: "var(--text-secondary)" }}
      >
        <span className="inline-flex items-center gap-1.5">
          <MapPin className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
          推荐地图 · {points.length} 个地点
        </span>
        {collapsed ? (
          <ChevronDown className="w-3.5 h-3.5" />
        ) : (
          <ChevronUp className="w-3.5 h-3.5" />
        )}
      </button>

      {!collapsed && (
        <div className="px-3 pb-3 space-y-2">
          {jsKey && !loadError ? (
            <div
              ref={containerRef}
              className="w-full h-[160px] rounded-lg overflow-hidden"
              style={{ border: "1px solid var(--border)" }}
            />
          ) : staticUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={staticUrl}
              alt="推荐地点地图"
              className="w-full h-[160px] object-cover rounded-lg"
              style={{ border: "1px solid var(--border)" }}
            />
          ) : (
            <div
              className="h-[120px] flex items-center justify-center text-[11px] rounded-lg"
              style={{ border: "1px dashed var(--border)", color: "var(--text-muted)" }}
            >
              未配置地图 Key
            </div>
          )}

          <div className="flex items-center justify-between gap-2">
            <p className="text-[10px] truncate" style={{ color: "var(--text-muted)" }}>
              {loadError ? "交互地图不可用，已显示静态地图" : "点击标记可切换当前卡片"}
            </p>
            <a
              href={buildAmapMarkerUrl(activePoint.lng, activePoint.lat, activePoint.name)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] font-medium shrink-0"
              style={{ color: "var(--accent)" }}
            >
              打开导航
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
