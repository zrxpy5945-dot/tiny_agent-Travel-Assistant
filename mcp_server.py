"""最简单的 MCP Server —— 给 agent 提供可复用的额外工具"""
import requests
from mcp.server.fastmcp import FastMCP

from rag import search

mcp = FastMCP("TinyAgent Tools")

_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def _geocode(city: str):
    """城市名 -> (纬度, 经度, 城市标准名)，找不到返回 None。"""
    resp = requests.get(
        _GEO_URL,
        params={"name": city, "count": 1, "language": "zh", "format": "json"},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        return None
    top = results[0]
    return top["latitude"], top["longitude"], top.get("name", city)


def _aqi_level(aqi: float) -> str:
    """欧洲 AQI 分档转中文。"""
    if aqi <= 20:
        return "优"
    if aqi <= 40:
        return "良"
    if aqi <= 60:
        return "中等"
    if aqi <= 80:
        return "较差"
    if aqi <= 100:
        return "很差"
    return "极差"


@mcp.tool()
def calculate(a: float, b: float, op: str) -> str:
    """
    计算两个数的四则运算。
    当用户问"算一下"、"多少加多少"、"数学题"、"计算"等问题时调用。
    op 必须是 '+'、'-'、'*'、'/' 之一。
    """
    if op == '+':
        r = a + b
    elif op == '-':
        r = a - b
    elif op == '*':
        r = a * b
    elif op == '/':
        if b == 0:
            return "除数不能为零"
        r = a / b
    else:
        return f"不支持的运算符：{op}，只能用 + - * /"
    return f"{a} {op} {b} = {r}"


@mcp.tool()
def reverse_text(text: str) -> str:
    """
    把一段文字反转。
    当用户说"反转"、"倒过来"、"反过来"、"逆向"、"倒序"等关键词时调用。
    """
    return text[::-1]


@mcp.tool()
def get_air_quality(city: str) -> str:
    """
    查询指定城市的实时空气质量和 PM2.5 浓度。
    当用户问"空气质量"、"雾霾"、"PM2.5"、"要不要戴口罩"、"适不适合跑步或户外运动"时调用。
    city 用中文城市名，例如"北京"、"上海"。
    """
    try:
        coord = _geocode(city)
    except requests.RequestException as e:
        return f"查询{city}失败：网络异常（{e}）"
    if coord is None:
        return f"没找到城市「{city}」，换个写法试试"

    lat, lon, name = coord
    try:
        resp = requests.get(
            _AQ_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "european_aqi,pm2_5",
            },
            timeout=15,
        )
        resp.raise_for_status()
        current = resp.json()["current"]
        aqi = current["european_aqi"]
        pm25 = current.get("pm2_5")
    except requests.RequestException as e:
        return f"查询{name}空气质量失败：网络异常（{e}）"
    except (KeyError, ValueError) as e:
        return f"查询{name}空气质量失败：数据格式异常（{e}）"

    pm25_text = f"{pm25} μg/m³" if pm25 is not None else "暂无数据"
    return f"{name}空气质量：AQI {aqi}（{_aqi_level(aqi)}），PM2.5 {pm25_text}"


@mcp.tool()
def search_travel_guide(query: str) -> str:
    """
    在本地旅游知识库中检索资料。
    当用户问行程怎么安排、有什么好玩、要不要提前预约、能不能带某物品、怎么去某个景点
    这类需要查资料的问题时调用。实时天气和空气质量不要用这个工具。
    如果返回"没有找到"，请如实告诉用户你没有这方面资料，不要自己编造。
    """
    hits = search(query, top_k=3)
    if not hits:
        return "知识库中没有找到相关内容，请如实告诉用户你不确定。"

    parts = []
    for hit in hits:
        parts.append(f"【来源：{hit['source']}】\n{hit['text']}")
    return "\n\n".join(parts)


if __name__ == "__main__":
    mcp.run()   # 不传参数默认就是 stdio transport，正好给 agent 当子进程起
