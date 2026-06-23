/**
 * Amap key resolution — Web 服务 Key 与 JS API Key 分离（Day 6.7）.
 *
 * - NEXT_PUBLIC_AMAP_JS_KEY: 浏览器 JS API 2.0 交互地图
 * - NEXT_PUBLIC_AMAP_WEB_SERVICE_KEY: 前端静态地图兜底（Web 服务 REST）
 *
 * 两者在高德控制台通常对应不同 Key；请勿混用 Key 类型。
 */

/** JS API 2.0 Key — 用于 @amap/amap-jsapi-loader 交互地图。 */
export function getAmapJsKey(): string | null {
  const key = process.env.NEXT_PUBLIC_AMAP_JS_KEY?.trim();
  return key ? key : null;
}

/** Web 服务 Key — 用于静态地图等 REST 兜底（非 JS Key）。 */
export function getAmapWebServiceKey(): string | null {
  const key = process.env.NEXT_PUBLIC_AMAP_WEB_SERVICE_KEY?.trim();
  return key ? key : null;
}

export function hasAmapJsKey(): boolean {
  return getAmapJsKey() != null;
}

export function hasAmapWebServiceKey(): boolean {
  return getAmapWebServiceKey() != null;
}
