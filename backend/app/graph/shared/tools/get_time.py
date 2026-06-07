"""获取当前详细时间的tool"""
from datetime import datetime

from langchain_core.tools import tool

@tool
def get_time(query: str = "") -> str:
    """返回当前详细时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
