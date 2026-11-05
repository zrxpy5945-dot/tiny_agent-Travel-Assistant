"""工具定义：真实天气查询，数据源 Open-Meteo（免费、无需 key、国内稳定）。"""
from datetime import datetime
import requests

# WMO 天气代码 -> 中文描述
WEATHER_CODE = {
    0: "晴",
    1: "晴间多云",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "大毛毛雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴大冰雹",
}

# 风向度数 -> 八方位
_DIRS = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]


def get_weather(city: str) -> str:
    """查询城市当前天气，返回一段可直接给模型阅读的文本。"""
    try:
        # 第一步：城市名 -> 经纬度
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "zh"},
            timeout=15,
        )
        geo.raise_for_status()
        results = geo.json().get("results")
        if not results:
            return f"没有找到「{city}」这个城市，换个写法试试"

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        location = results[0].get("name") or city

        # 第二步：经纬度 -> 当前天气
        weather = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "weather_code,wind_speed_10m,wind_direction_10m"
                ),
                "timezone": "auto",
            },
            timeout=15,
        )
        weather.raise_for_status()
        cur = weather.json()["current"]

    except requests.RequestException as e:
        return f"查询 {city} 的天气失败，网络异常：{e}"
    except (KeyError, IndexError, ValueError):
        return f"没有查到 {city} 的天气，可能是城市名无法识别"

    desc = WEATHER_CODE.get(cur["weather_code"], f"未知天气({cur['weather_code']})")
    wind_dir = _DIRS[round(cur["wind_direction_10m"] / 45) % 8]

    return (
        f"{location} 当前{desc}，"
        f"气温 {cur['temperature_2m']}°C，体感 {cur['apparent_temperature']}°C，"
        f"湿度 {cur['relative_humidity_2m']}%，"
        f"风速 {cur['wind_speed_10m']} km/h，风向 {wind_dir}"
    )

_WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

def get_current_time() -> str:
    """返回本机当前的日期、星期和具体时间。"""
    now = datetime.now()
    return f"当前时间 {now.strftime('%Y年%m月%d日 %H:%M:%S')}，{_WEEKDAYS[now.weekday()]}"

# 给模型看的"菜单"
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "查询指定城市当前的天气、温度、湿度和风力。"
                "当用户询问某个城市天气、气温、要不要带伞、穿什么、适合出行时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如 北京、上海",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": (
                "查询当前的日期、星期和具体时刻。"
                "当用户询问现在几点、今天几号、今天星期几、今天是什么时间时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    }
]

# 名字 -> 真正的函数
tool_map = {"get_weather": get_weather,"get_current_time": get_current_time}
