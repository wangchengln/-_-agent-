#!/usr/bin/env python3
"""Live integration smoke test for Amap Web Service API."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _print_header(title: str) -> None:
    print("=" * 60)
    print(title)
    print("=" * 60)


def test_amap_integration(
    *,
    address: str = "上海市人民广场",
    keywords: str = "咖啡",
    lng: float = 121.475,
    lat: float = 31.233,
) -> bool:
    from tools.amap_client import AmapClient, AmapClientError, AmapConfigError

    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        print("[FAIL] 未设置 AMAP_API_KEY，请在 backend/.env 中配置")
        return False

    client = AmapClient(api_key=api_key)
    print(f"[INFO] API Key: {api_key[:6]}...")

    try:
        print(f"\n[1/5] 地理编码: {address}")
        location = client.geocode(address, city="上海")
        print(f"  [OK] {location.address}")
        print(f"     坐标: {location.to_amap_location()}  adcode={location.adcode}")

        print(f"\n[2/5] 逆地理编码: {location.to_amap_location()}")
        reverse = client.regeocode(location.lng, location.lat)
        print(f"  [OK] {reverse.address}")

        print(f"\n[3/5] 周边搜索: {keywords} (半径 2000m)")
        pois = client.search_around(
            location.lng,
            location.lat,
            keywords=keywords,
            radius=2000,
            offset=5,
            anchor_city=location.city,
        )
        if not pois:
            print("  [WARN] 未找到 POI（可能是关键词或配额问题）")
        else:
            print(f"  [OK] 找到 {len(pois)} 个 POI")
            for index, poi in enumerate(pois[:5], start=1):
                distance = f"{poi.distance_m:.0f}m" if poi.distance_m else "N/A"
                rating = poi.rating if poi.rating is not None else "N/A"
                print(f"     {index}. {poi.name} | {poi.type} | {distance} | 评分={rating}")

        adcode = location.adcode or "310101"
        print(f"\n[4/5] 天气查询: adcode={adcode}")
        weather = client.weather(adcode, extensions="all")
        live = weather.lives[0] if weather.lives else None
        if live and live.weather:
            print(
                f"  [OK] {live.city} {live.weather} {live.temperature}C "
                f"(report: {live.reporttime})"
            )
        elif weather.casts:
            cast = weather.casts[0]
            print(
                f"  [OK] 预报 {cast.date} 白天{cast.dayweather} {cast.daytemp}C "
                f"夜间{cast.nightweather} {cast.nighttemp}C"
            )
        else:
            print("  [WARN] 未返回天气数据")
        print(f"     is_rainy={weather.is_rainy}")

        if len(pois) >= 1:
            dest = pois[0].location
            print(f"\n[5/5] 步行路径: 人民广场 -> {pois[0].name}")
            route = client.plan_walking_route(location, dest)
            print(
                f"  [OK] 距离 {route.distance_m}m, 预计 {route.duration_s // 60} 分钟"
            )
        else:
            print("\n[5/5] 步行路径: 跳过（无 POI 结果）")

        return True

    except AmapConfigError as exc:
        print(f"[FAIL] 配置错误: {exc}")
        return False
    except AmapClientError as exc:
        print(f"[FAIL] Amap 调用失败: {exc}")
        return False
    except Exception as exc:
        print(f"[FAIL] 未知错误: {exc}")
        return False


if __name__ == "__main__":
    address_arg = sys.argv[1] if len(sys.argv) > 1 else "上海市人民广场"
    keywords_arg = sys.argv[2] if len(sys.argv) > 2 else "咖啡"

    _print_header("Amap API 集成测试")
    ok = test_amap_integration(address=address_arg, keywords=keywords_arg)
    _print_header("测试结果")
    if ok:
        print("[OK] 集成测试通过")
        sys.exit(0)
    print("[FAIL] 集成测试失败")
    print("\n使用说明:")
    print("1. 在 https://console.amap.com/ 申请 Web 服务 Key")
    print("2. 在 backend/.env 设置 AMAP_API_KEY=your_key")
    print("3. 运行: python test_amap.py [地址] [关键词]")
    print("   示例: python test_amap.py 上海市人民广场 咖啡")
    sys.exit(1)
