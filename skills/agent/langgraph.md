# LangGraph Notes

本文件用于沉淀项目中的 LangGraph 设计约束。

当前已确认规则：

- 不要在请求期间重复构建 graph。
- Graph、LLM、Redis、HTTP Client、Langfuse 等应用级资源应在 lifespan 或工厂函数中初始化。
- Graph 层只负责 Agent 编排，不直接依赖 HTTP 请求对象。
