# Backend

本文件说明 `backend/` 已提供的能力、启动与测试方式，以及分层约束。

## 当前实现

后端已经具备以下可确认能力：

- 健康检查：`GET /health`、`GET /ready`
- 会话管理：`POST /v1/conversations`、`GET /v1/conversations`、`GET /v1/conversations/{conversation_id}`、`GET /v1/conversations/{conversation_id}/messages`、`DELETE /v1/conversations/{conversation_id}`
- 文件管理：`GET /v1/files`、`GET /v1/files/{file_id}`、`GET /v1/files/{file_id}/download`、`DELETE /v1/files/{file_id}`、`POST /v1/files/upload`

`GET /v1/files` 返回 `{ items, total }` 结构的用户范围分页列表，和会话、运行记录列表接口保持一致，便于前端统一接入列表页状态管理。
`POST /v1/files/upload` 会先把上传字节写入本地对象存储，再持久化 `storage_key` 与存储状态元数据，同时登记一条初始 `documents` 记录，并在文件元数据中回填 `document_id` 与 `document_status`。
仓库还提供一条最小文档处理基础链路：`app.tasks.document_indexing.index_document()` 会读取已上传文本类文件的对象存储内容，做 UTF-8 解码与规范化文本压缩，再把对应 `documents` 记录标记为 `indexed`，同时回写 `files.metadata.document_status=indexed`。
`GET /v1/files/{file_id}` 可直接读取单个文件元数据，`GET /v1/files/{file_id}/download` 可在用户范围内下载已存储的二进制内容。
`DELETE /v1/files/{file_id}` 会在用户范围内软删除文件元数据、软删除关联 `documents` 记录，并尽量同步清理对象存储中的二进制内容。
`POST /v1/files/upload` 与 `DELETE /v1/conversations/{conversation_id}` 的成功路径现在也会通过数据库 writer 写入 `audit_logs`，同时保持审计失败不影响主业务。
- Agent 控制与查询：`GET /v1/agent/runs`、`GET /v1/agent/runs/{run_id}`、`GET /v1/agent/status`、`POST /v1/agent/resume`、`POST /v1/agent/interrupt`、`POST /v1/agent/cancel`
`POST /v1/agent/resume`、`POST /v1/agent/interrupt` 与 `POST /v1/agent/cancel` 的成功路径现在也会通过数据库 writer 写入 `audit_logs`，同时保持审计失败不影响主业务。
- 聊天：`POST /v1/chat`、`POST /v1/chat/stream`
- 多 Agent 查询与调用：`GET /v1/agents`、`GET /v1/agents/{agent_id}`、`POST /v1/agents/{agent_id}/chat`、`POST /v1/agents/{agent_id}/chat/stream`

当前后端的 Agent 层采用 `Agent Registry + 多个独立 Graph` 结构，对外暴露 `chat_agent` 和 `code_agent` 两个独立能力。它们不是 supervisor 协作关系，也不做 handoff。
`POST /v1/chat` 与 `POST /v1/chat/stream` 继续保留为兼容入口，默认分别等价于 `POST /v1/agents/chat_agent/chat` 与 `POST /v1/agents/chat_agent/chat/stream`。
`conversations` 与 `agent_runs` 现在都已提供正式 `agent_id` 字段，`metadata.agent_id` 仅作为兼容旧数据和旧响应链路的兜底来源。
当前聊天链路已经切换到标准 LangGraph checkpoint 模式：默认用会话级 `conversation_id` 作为 `thread_id`，普通对话只提交本轮增量消息，历史上下文由 checkpoint 恢复，数据库消息主要承担前端展示、审计与旧会话初始化回填职责。

其中 `POST /v1/chat` 已接入基础持久化流程，会在非流式调用中写入：

- conversation
- request / response messages
- agent run
- chat audit event（成功路径会通过数据库 writer 落库到 `audit_logs`）

`POST /v1/chat/stream` 现在也会在 Service 层接入基础持久化编排，在保持 SSE 输出的同时补齐：

- conversation 解析或创建
- request messages 写入
- agent run 创建、完成或失败更新
- done 事件中的最终 response 落库

此外，`GET /v1/conversations/{conversation_id}` 会返回会话元信息和已持久化消息列表，形成“写入聊天 -> 读取会话详情”的基础闭环。
如果前端只需要独立读取消息历史而不必同时取会话元信息，也可以使用 `GET /v1/conversations/{conversation_id}/messages` 获取分页消息列表。
`GET /v1/agent/runs` 与 `GET /v1/agent/runs/{run_id}` 也可直接读取已持久化的运行记录摘要与详情，并补充 `started_at`、`updated_at`、终态下的 `finished_at`、`duration_ms`，以及失败/中断场景的原因摘要字段，为 Agent Runs 页面提供更完整的状态信息。
其中详情接口还会返回该次运行对应的已持久化 `tool_calls`，用于 run detail 页展示工具调用轨迹。
其中列表接口还支持按 `status` 与 `conversation_id` 做用户范围内筛选，方便运行记录页直接接入筛选条件。

当前运行控制遵循以下语义：

- `thread_id` 默认绑定会话级 `conversation_id`，承载同一会话的 checkpoint 状态。
- `run_id` 仅用于运行控制、审计和详情查询，不再作为多轮记忆主键。
- `interrupt`：尝试停止当前运行，并保留可恢复的 checkpoint。
- `resume`：仅允许恢复 `interrupted` 状态的既有运行，不会新建新的 run。
- `cancel`：彻底取消当前运行，并把状态落为 `cancelled`，后续不再允许恢复。
- 如果恢复目标缺少可用 checkpoint，接口会直接返回错误，而不是模拟一次恢复成功。
- 为兼容旧数据，恢复时会优先读取会话级 thread，必要时再回退到旧的 `run_id` thread。

为了支撑真实恢复，后端会在启动期初始化 LangGraph checkpoint。默认可通过 `AGENT_CHECKPOINT_ENABLED` 控制开关，并用 `AGENT_CHECKPOINT_URL` 指定独立连接串；留空时会复用 `DATABASE_URL` 并自动转换成 `psycopg` 可用格式。
`AGENT_CHECKPOINT_CONNECT_TIMEOUT_SECONDS` 用于限制 PostgreSQL checkpoint 初始化等待时间，避免本地数据库不可用时长时间阻塞启动。
如果 PostgreSQL checkpoint 初始化失败，系统会降级为进程内内存 checkpoint，用于本地调试兜底；但这不适合依赖进程重启后的持久化恢复场景。

## 分层约束

当前后端继续遵循以下边界：

- API 层只处理 HTTP 输入输出、依赖注入与异常映射
- Service 层负责业务编排和事务边界
- Repository 层只负责数据访问，不主动 `commit`
- Graph 层只负责 Agent 编排，不直接依赖 HTTP 请求对象
- Graph、LLM、Redis、HTTP Client、Langfuse 等应用级资源在启动阶段初始化
- Agent graph 通过 registry 在启动阶段统一编译，不在请求期间重复 build

## 启动与迁移

在 `backend/` 目录执行：

```bash
python run.py
```

或：

```bash
uvicorn app.main:app --reload
```

数据库迁移命令：

```bash
alembic upgrade head
alembic revision --autogenerate -m "message"
```

当前本地对象存储相关环境变量：

- `OBJECT_STORAGE_BACKEND=local`
- `OBJECT_STORAGE_LOCAL_ROOT=data/object_storage`

`GET /ready` 会额外返回 `object_storage` 状态块，用于区分对象存储是否已禁用、可用，或已启用但暂时不可用。
当前最小文档索引流程只支持文本类 MIME：`text/plain`、`text/markdown`、`application/json`、`application/xml`、`text/csv`。不支持的二进制格式会先显式返回“解析器未配置”，也为更丰富的 parser 扩展预留清晰边界。

## 测试

在 `backend/` 目录执行：

```bash
python -m pytest
```

当前测试重点覆盖：

- API 基础行为
- Conversation / File / AgentRun / Chat Service
- Document indexing 最小处理链路与 task wrapper
- ORM 注册与基础 Repository 行为

## 注意点

- 后端内部 import 统一使用 `app.xxx`
- 当前用户体系为轻量实现，匿名用户与 API Key 用户会按需写入 `users` 记录，用于支撑会话、文件与运行记录的归属关系
- 详细代码结构与目录边界请以 `backend/` 现有代码、[AGENTS.md](../AGENTS.md) 与 [项目目录结构.txt](../项目目录结构.txt) 为准
