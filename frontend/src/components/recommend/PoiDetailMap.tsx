"use client";

import { useEffect, useRef, useState } from "react";
import AMapLoader from "@amap/amap-jsapi-loader";
import { MapPin } from "lucide-react";
import { getAmapJsKey, getAmapWebServiceKey } from "@/lib/amap-config";
import { buildAmapMarkerUrl } from "@/lib/recommend-types";

interface Props {
  lng: number;
  lat: number;
  name: string;
  className?: string;
}

export default function PoiDetailMap({ lng, lat, name, className = "" }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<AMap.Map | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const jsKey = getAmapJsKey();
  const webKey = getAmapWebServiceKey();
  const staticUrl =
    webKey &&
    `https://restapi.amap.com/v3/staticmap?key=${encodeURIComponent(webKey)}&location=${lng},${lat}&zoom=15&size=640*240&scale=2&markers=mid,0x1677ff,1:${lng},${lat}`;

  useEffect(() => {
    if (!jsKey || !containerRef.current) return;

    let cancelled = false;
    setLoadError(null);

    AMapLoader.load({
      key: jsKey,
      version: "2.0",
      plugins: ["AMap.Scale"],
    })
      .then((AMap) => {
        if (cancelled || !containerRef.current) return;
        const map = new AMap.Map(containerRef.current, {
          viewMode: "2D",
          zoom: 15,
          center: [lng, lat],
        });
        map.add(new AMap.Scale());
        const marker = new AMap.Marker({
          position: [lng, lat],
          title: name,
        });
        marker.setMap(map);
        mapRef.current = map;
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "地图加载失败");
        }
      });

    return () => {
      cancelled = true;
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
      }
    };
  }, [jsKey, lng, lat, name]);

  if (staticUrl && (!jsKey || loadError)) {
    return (
      <div className={`rounded-xl overflow-hidden ${className}`} style={{ border: "1px solid var(--border)" }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={staticUrl} alt={`${name} 地图`} className="w-full h-[180px] object-cover" />
        <div className="px-3 py-2 flex items-center justify-between gap-2">
          <span className="text-[11px] truncate" style={{ color: "var(--text-muted)" }}>
            {loadError ? "交互地图不可用，已显示静态地图" : "静态地图"}
          </span>
          <a
            href={buildAmapMarkerUrl(lng, lat, name)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] shrink-0 font-medium"
            style={{ color: "var(--accent)" }}
          >
            导航
          </a>
        </div>
      </div>
    );
  }

  if (!jsKey) {
    return (
      <div
        className={`rounded-xl flex items-center justify-center h-[180px] text-[12px] ${className}`}
        style={{ border: "1px solid var(--border)", color: "var(--text-muted)" }}
      >
        <MapPin className="w-4 h-4 mr-1.5" />
        未配置地图 Key
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl overflow-hidden ${className}`}
      style={{ border: "1px solid var(--border)" }}
    >
      <div ref={containerRef} className="w-full h-[180px]" />
    </div>
  );
}
