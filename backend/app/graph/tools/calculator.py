from __future__ import annotations


async def calculator_tool(expression: str) -> dict:
    try:
        value = eval(expression, {"__builtins__": {}}, {})
    except Exception as exc:
        return {"expression": expression, "error": str(exc)}
    return {"expression": expression, "value": value}
