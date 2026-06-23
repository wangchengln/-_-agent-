/* Minimal Amap JS API 2.0 typings for Day 6.7 map embedding. */

declare namespace AMap {
  class Pixel {
    constructor(x: number, y: number);
  }

  class LngLat {
    constructor(lng: number, lat: number);
  }

  class Map {
    constructor(container: HTMLElement | string, opts?: Record<string, unknown>);
    add(control: unknown): void;
    setCenter(center: [number, number]): void;
    setZoomAndCenter(zoom: number, center: [number, number]): void;
    setFitView(
      overlays?: unknown[],
      immediately?: boolean,
      avoid?: [number, number, number, number]
    ): void;
    destroy(): void;
  }

  class Marker {
    constructor(opts?: Record<string, unknown>);
    on(event: string, handler: () => void): void;
    setMap(map: Map | null): void;
  }

  class Polyline {
    constructor(opts?: Record<string, unknown>);
    setMap(map: Map | null): void;
  }

  class InfoWindow {
    constructor(opts?: Record<string, unknown>);
    setContent(content: string | HTMLElement): void;
    open(map: Map, position: [number, number]): void;
  }

  class Scale {
    constructor(opts?: Record<string, unknown>);
  }

  class ToolBar {
    constructor(opts?: Record<string, unknown>);
  }
}

declare module "@amap/amap-jsapi-loader" {
  interface LoadOptions {
    key: string;
    version: string;
    plugins?: string[];
  }

  export default class AMapLoader {
    static load(options: LoadOptions): Promise<typeof AMap>;
  }
}
