"""最简单的 MCP Server —— 演示用，给 agent 提供两个额外工具"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TinyAgent Tools")

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

if __name__ == "__main__":
    mcp.run()   # 不传参数默认就是 stdio transport，正好给 agent 当子进程起