"""MCP Client 封装 """
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

# MCP 服务器启动参数：用 python 运行同目录下的 mcp_server.py
SERVER = StdioServerParameters(command="python", args=["mcp_server.py"])


# 异步内部函数：启动服务器子进程，建立 MCP 会话，获取服务器提供的所有工具列表
async def _async_list_tools():
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return result.tools


# 异步内部函数：启动服务器子进程，建立 MCP 会话，调用指定名称的工具并返回文本结果
async def _async_call_tool(name: str, arguments: dict) -> str:
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            texts = [c.text for c in result.content if hasattr(c, "text")]
            return "\n".join(texts) if texts else "(工具未返回文本)"


# 对外同步接口：列出 MCP 服务器所有工具，并转换为 LLM function calling 格式的 schema
def get_mcp_tools_schema() -> list[dict]:
    try:
        tools = asyncio.run(_async_list_tools())
    except Exception as e:  # MCP 客户端用 TaskGroup 抛错，ExceptionGroup 也在这里兜住
        print(f"  [警告] MCP Server 连接失败，本次仅使用本地工具：{e}")
        return []
    schema_list = []
    for t in tools:
        input_schema = t.inputSchema or {"type": "object", "properties": {}}
        schema_list.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": input_schema,
            },
        })
    return schema_list


# 单次 MCP 工具调用最多等 20 秒，防止子进程卡死导致无限阻塞
TOOL_TIMEOUT = 20


async def _call_with_timeout(name: str, arguments: dict) -> str:
    return await asyncio.wait_for(
        _async_call_tool(name, arguments), timeout=TOOL_TIMEOUT
    )


# 对外同步接口：调用指定 MCP 工具，返回工具执行的文本结果
def call_mcp_tool(name: str, arguments: dict) -> str:
    try:
        return asyncio.run(_call_with_timeout(name, arguments))
    except asyncio.TimeoutError:
        return f"调用工具 {name} 超时（超过 {TOOL_TIMEOUT} 秒），请稍后再试"
    except Exception as e:
        # 返回明确的失败文本而不是空串，让模型知道"工具坏了"而不是"没查到"
        return f"调用工具 {name} 失败：{e}"