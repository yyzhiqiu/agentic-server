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
- Agent 控制与查询：`GET /v1/agent/runs`、`GET /v1/agent/runs/{run_id}`、`GET /v1/agent/status`、`POST /v1/agent/resume`、`POST /v1/agent/interrupt`
`POST /v1/agent/resume` 与 `POST /v1/agent/interrupt` 的成功路径现在也会通过数据库 writer 写入 `audit_logs`，同时保持审计失败不影响主业务。
- 聊天：`POST /v1/chat`、`POST /v1/chat/stream`

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

## 分层约束

当前后端继续遵循以下边界：

- API 层只处理 HTTP 输入输出、依赖注入与异常映射
- Service 层负责业务编排和事务边界
- Repository 层只负责数据访问，不主动 `commit`
- Graph 层只负责 Agent 编排，不直接依赖 HTTP 请求对象
- Graph、LLM、Redis、HTTP Client、Langfuse 等应用级资源在启动阶段初始化

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
