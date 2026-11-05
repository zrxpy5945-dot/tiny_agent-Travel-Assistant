"""Agent 核心：LLM + 工具 + 循环"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from tools import tool_map, tools_schema

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-flash"
MAX_STEPS = 5  # 防止模型反复调工具陷入死循环

SYSTEM_PROMPT = (
    "你是一个贴心的出行助手。"
    "凡是涉及天气、温度的问题，必须先调用 get_weather 工具查询，不要凭自己的知识猜测。"
    "拿到数据后，结合天气、温度、湿度给出具体的出行建议，例如穿衣、带伞、防晒、是否适合户外活动。"
    "回答简洁，控制在 120 字以内。"
)

def _trim_history(messages: list) -> None:
    """原地裁掉工具调用的中间消息，只留干净的对话历史。"""
    # 要删的下标，倒着删避免索引错乱
    to_remove = []
    for i, msg in enumerate(messages):
        role = msg["role"] if isinstance(msg, dict) else msg.role
        if role == "tool":
            to_remove.append(i)
        elif role == "assistant":
            # OpenAI SDK 返回的 ChatCompletionMessage 对象有 tool_calls 属性
            has_calls = (
                msg.tool_calls
                if hasattr(msg, "tool_calls")
                else msg.get("tool_calls")
            )
            if has_calls:
                to_remove.append(i)
    for i in reversed(to_remove):
        del messages[i]

def run_agent(user_input: str, messages: list) -> str:
    """输入用户问题，返回最终回答。"""
    mcp_tools =tools_schema
    messages.append({"role": "user", "content": user_input})

    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools_schema,
        )
        msg = resp.choices[0].message

        # 没有工具调用，说明模型已给出最终答案，循环结束
        if not msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content})
            _trim_history(messages)
            return msg.content

        # 模型想调工具：先把它的请求记进对话历史
        messages.append(msg)

        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"  [工具调用] {name}({args})")

            func = tool_map.get(name)
            result = func(**args) if func else f"未知工具：{name}"
            print(f"  [工具返回] {result}")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )
    _trim_history(messages)
    return "已达到最大循环次数，任务未完成。"
