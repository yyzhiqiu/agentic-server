# Backend Architecture

本文件用于沉淀 `backend/` 的分层边界、资源初始化方式与演进约束。

## 分层边界

- `api/` 只处理 HTTP 输入输出、依赖注入与异常映射。
- `services/` 负责业务编排、事务边界和跨模块协作。
- `db/repositories/` 只负责数据访问，不主动 `commit`。
- `graph/` 只负责 Agent 编排，不直接依赖 HTTP 请求对象。

## 资源初始化

- Graph、LLM、Redis、HTTP Client、Langfuse 等应用级资源应在启动阶段或工厂函数中初始化。
- 请求处理期间不重复构建 Graph，也不在路由层拼装基础设施客户端。

## 代码约束

- 后端内部 Python 包名固定为 `app`。
- 后端内部 import 统一使用 `app.xxx`。
- 修改 Python 模块时，优先遵循 [../../skills/ai/python-commenting.md](../../skills/ai/python-commenting.md)。
