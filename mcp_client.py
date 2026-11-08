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
    tools = asyncio.run(_async_list_tools())
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


# 对外同步接口：调用指定 MCP 工具，返回工具执行的文本结果
def call_mcp_tool(name: str, arguments: dict) -> str:
    return asyncio.run(_async_call_tool(name, arguments))