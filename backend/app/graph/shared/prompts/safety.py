"""多个 Agent 共享的安全边界提示词。"""

from __future__ import annotations


SAFETY_PROMPT = (
    "不要捏造外部执行结果。"
    "当缺少权限、工具或上下文时，应明确说明限制，并给出安全替代方案。"
)

