"""
MCP Server：以 MCP 协议暴露外部服务类工具。
Agent 通过 langchain-mcp-adapters 以 stdio 方式连接本 server，
工具名与本地工具注册表（tools.py）互不冲突。

启动方式（由 MCP 客户端自动拉起）：
    python -m app.agents.mcp_server
"""
import os
import sys
import logging

# 自举：无论以何种方式（-m 或直接运行）被拉起，都能 import app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 压掉 MCP 协议自身的 INFO 日志，保持进程输出干净
logging.getLogger("mcp").setLevel(logging.WARNING)

import requests
from datetime import datetime, timezone, timedelta

from mcp.server.fastmcp import FastMCP

from app.core.config import AMAP_API_KEY
from app.core.resilience import resilient_call

# stdio 传输，客户端通过 JSON 配置自动启动本进程
mcp = FastMCP("taskbench-external")


@mcp.tool()
def get_current_time() -> str:
    """获取当前日期和时间（北京时间），无需参数，用于回答时间相关问题时准确推算日期"""
    now = datetime.now(timezone.utc) + timedelta(hours=8)
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return (
        f"现在是 {now.year}年{now.month}月{now.day}日 "
        f"星期{weekdays[now.weekday()]} "
        f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}（北京时间）"
    )


@resilient_call("amap")
def _amap_geo(key: str, city: str):
    """带重试+熔断的高德地理编码"""
    return requests.get(
        "https://restapi.amap.com/v3/geocode/geo",
        params={"key": key, "address": city}, timeout=10,
    )


@resilient_call("amap")
def _amap_weather(key: str, adcode: str):
    """带重试+熔断的高德天气查询"""
    return requests.get(
        "https://restapi.amap.com/v3/weather/weatherInfo",
        params={"key": key, "city": adcode, "extensions": "all"}, timeout=10,
    )


@mcp.tool()
def query_weather(city: str) -> str:
    """查询城市天气，参数 city（城市名，如'北京'或'杭州'），返回当天及未来几天天气"""
    key = AMAP_API_KEY
    if not key:
        return "未配置高德 API Key，请在 .env 中设置 AMAP_API_KEY"

    try:
        geo_data = _amap_geo(key, city).json()
        if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
            return f"未找到城市「{city}」，请检查城市名是否正确"

        adcode = geo_data["geocodes"][0]["adcode"]
        city_name = geo_data["geocodes"][0].get("formatted_address", city)

        weather_data = _amap_weather(key, adcode).json()
        if weather_data.get("status") != "1":
            return f"查询天气失败：{weather_data.get('info', '未知错误')}"

        forecasts = weather_data.get("forecasts", [])
        if not forecasts:
            return f"{city_name} 暂无天气数据"

        f = forecasts[0]
        lines = [f"📍 {f.get('province', '')}{f.get('city', city_name)} 天气"]
        for day in f.get("casts", []):
            lines.append(
                f"{day['date']}  {day['dayweather']}  "
                f"{day['nighttemp']}°C ~ {day['daytemp']}°C  "
                f"{day['daywind']}风{day['daypower']}级"
            )
        return "\n".join(lines)
    except requests.RequestException as e:
        return f"网络请求失败: {e}"
    except Exception as e:
        return f"查询天气出错: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
