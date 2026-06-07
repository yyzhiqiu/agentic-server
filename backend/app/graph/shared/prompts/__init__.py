"""多个 Agent 共享的提示词片段。"""

from app.graph.shared.prompts.format import FORMAT_PROMPT
from app.graph.shared.prompts.safety import SAFETY_PROMPT
from app.graph.shared.prompts.system import BASE_SYSTEM_PROMPT

__all__ = [
    "BASE_SYSTEM_PROMPT",
    "FORMAT_PROMPT",
    "SAFETY_PROMPT",
]

