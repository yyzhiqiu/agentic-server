# backend

`backend/` 是本仓库的后端服务目录，采用 `FastAPI + LangGraph` 结构，内部 Python 包名固定为 `app`。

## 已提供能力

当前仓库中可以直接确认的后端接口包括：

- `GET /health`
- `GET /ready`
- `GET /v1/agent/runs`
- `GET /v1/agent/runs/{run_id}`
- `GET /v1/agents`
- `GET /v1/agents/{agent_id}`
- `POST /v1/agents/{agent_id}/chat`
- `POST /v1/agents/{agent_id}/chat/stream`
- `POST /v1/chat`
- `POST /v1/chat/stream`
- `GET /v1/agent/status`
- `POST /v1/agent/resume`
- `POST /v1/agent/interrupt`
- `POST /v1/agent/cancel`
- `POST /v1/conversations`
- `GET /v1/conversations`
- `GET /v1/conversations/{conversation_id}`
- `GET /v1/conversations/{conversation_id}/messages`
- `DELETE /v1/conversations/{conversation_id}`
- `GET /v1/files`
- `GET /v1/files/{file_id}`
- `GET /v1/files/{file_id}/download`
- `DELETE /v1/files/{file_id}`
- `POST /v1/files/upload`

其中已经接入真实后端分层与数据库持久化的能力包括：

- `conversations`：用户范围内的创建、查询、软删除，删除成功路径会写入 `audit_logs`。
- `files`：上传元数据登记、列表查询、详情读取、下载与删除；列表接口返回 `{ items, total }` 分页结构，上传成功路径默认会把二进制内容写入本地对象存储、同步登记一条最小 `documents` 记录，并写入 `audit_logs`。删除会同时软删除文件元数据、软删除关联 `documents` 记录，并清理对象存储中的二进制内容。
- 当前聊天能力采用 `Agent Registry + 多个独立 Graph` 结构，对外暴露 `chat_agent` 和 `code_agent` 两个独立能力，不使用 supervisor，也不使用 handoff。
- `POST /v1/chat` 与 `POST /v1/chat/stream` 作为兼容入口保留，默认映射到 `chat_agent`。
- `conversations` 与 `agent_runs` 现已将 `agent_id` 持久化为正式字段，`metadata.agent_id` 仅保留为兼容旧数据与旧链路时的兜底来源。
- `documents`：已经具备一条最小可用的文档处理基础链路。上传文件后会先登记 `documents` 记录，随后可通过 `app.tasks.document_indexing.index_document()` 将文本类文件读取为规范化文本，并把 `documents.metadata.status` 与 `files.metadata.document_status` 更新为 `indexed`。
- `agent`：轻量 Agent Run 状态写入、恢复、可恢复中断、彻底取消，以及运行记录列表/详情查询；`resume` / `interrupt` / `cancel` 成功路径现在也会写入 `audit_logs`。
- `POST /v1/chat`：会话解析、消息写入、Agent Run 记录与审计事件，成功路径会通过数据库 writer 落库到 `audit_logs`。
- `POST /v1/chat/stream`：SSE 输出与基础会话 / 消息 / Agent Run 持久化编排。

当前聊天链路已经切换到标准 LangGraph checkpoint 模式：默认以会话级 `conversation_id` 作为 `thread_id` 持久化 `messages` 状态，普通对话只提交本轮增量消息，历史上下文优先由 checkpoint 恢复，数据库中的消息记录主要用于前端展示、审计与旧会话初始化回填。

`GET /v1/conversations/{conversation_id}` 也会返回该会话已持久化的消息列表，方便前端会话详情页直接消费。
如果前端只需要独立读取消息历史，也可以直接使用 `GET /v1/conversations/{conversation_id}/messages` 获取分页消息列表。
`GET /v1/agent/runs` 与 `GET /v1/agent/runs/{run_id}` 也可直接读取已持久化的运行记录摘要与详情，并返回 `started_at`、`updated_at`、终态下的 `finished_at`、`duration_ms`，以及失败/中断场景可直接展示的原因字段，方便前端列表和详情页直接消费。
其中 `GET /v1/agent/runs/{run_id}` 详情响应现在还会附带该次运行已持久化的 `tool_calls`，便于前端展示工具执行轨迹。
其中 `GET /v1/agent/runs` 还支持按 `status` 与 `conversation_id` 做用户范围内筛选，便于前端按状态或会话过滤运行记录。

## 目录结构

```text
backend/
├── app/                # 后端主包，内部 import 统一使用 app.xxx
├── migrations/         # Alembic 迁移目录
├── tests/              # pytest 测试目录
├── scripts/            # 后端本地脚本
├── .env.example        # 后端环境变量示例
├── requirements.txt    # Python 依赖
├── pyproject.toml      # pytest、ruff、项目配置
├── alembic.ini         # Alembic 配置入口
└── run.py              # 本地启动入口
```

`app/` 下已经包含以下主要分层：

- `api/`：HTTP 接口、依赖注入与异常映射
- `common/`：响应、错误码、异常、上下文等通用能力
- `core/`：配置、日志、安全与应用工厂
- `db/`：Session、Models、Repositories 与事务能力
- `integrations/`：Redis、HTTP Client、缓存、锁等外部基础设施集成
- `llms/`：模型工厂与降级策略
- `graph/`：LangGraph 多 Agent registry、shared 公共能力，以及 `chat_agent` / `code_agent` 独立 graph
- `services/`：业务编排与事务边界
- `observability/`：Trace、Langfuse、日志上下文与指标预留
- `audit/`：审计事件、服务与写入器
- `tasks/`：异步任务预留
- `utils/`：无业务状态的后端工具函数

## 启动方式

在 `backend/` 目录执行：

```bash
python run.py
```

或：

```bash
uvicorn app.main:app --reload
```

## 文件存储

后端默认使用本地文件系统对象存储：

- `OBJECT_STORAGE_BACKEND=local`
- `OBJECT_STORAGE_LOCAL_ROOT=data/object_storage`

`POST /v1/files/upload` 会先把上传字节写入对象存储，再持久化 `files.storage_key` 和存储状态元数据，同时登记一条初始 `documents` 记录，并在文件元数据里回填 `document_id` 与 `document_status`。
`GET /ready` 也会返回 `object_storage` 状态块，用于区分“对象存储已禁用”“对象存储可用”以及“对象存储已启用但当前不可用”三种情况。
最小文档索引流程目前只支持文本类文件：`text/plain`、`text/markdown`、`application/json`、`application/xml`、`text/csv`。这一步先保证基础链路稳定，同时为 PDF、DOCX 或图片等 richer parser 扩展预留边界。

## Agent 运行控制

当前 Agent Run 控制接口采用标准 LangGraph checkpoint 语义组织状态与恢复点：

- `thread_id` 默认绑定到会话级 `conversation_id`，用于承载同一会话的 checkpoint 状态。
- `run_id` 仅用于运行控制、审计和详情查询，不再承载多轮记忆。
- `POST /v1/chat` 与 `POST /v1/chat/stream` 在普通对话场景只提交本轮增量消息，旧消息由 checkpoint 恢复。
- `POST /v1/agent/interrupt`：尝试停止当前运行，并把状态落为 `interrupted`。如果 checkpoint 可用，后续允许恢复。
- `POST /v1/agent/resume`：仅允许恢复 `interrupted` 状态的运行，会从最近一次 checkpoint 继续执行，而不是新建一条运行；如果底层不存在可恢复 checkpoint，会直接拒绝恢复。
- `POST /v1/agent/cancel`：彻底取消当前运行，把状态落为 `cancelled`，后续不再允许恢复。
- 为兼容历史中断运行，恢复时会优先读取会话级 thread，必要时再回退到旧的 `run_id` thread。

与运行控制相关的环境变量如下：

- `AGENT_CHECKPOINT_ENABLED`：是否启用 LangGraph checkpoint 初始化。
- `AGENT_CHECKPOINT_URL`：可选的独立 checkpoint 连接串；留空时默认复用 `DATABASE_URL`，并自动转换为 `psycopg` 可用格式。
- `AGENT_CHECKPOINT_CONNECT_TIMEOUT_SECONDS`：PostgreSQL checkpoint 初始化超时时间，避免本地数据库不可用时长时间阻塞启动。

如果 PostgreSQL checkpoint 初始化失败，系统会自动降级为进程内内存 checkpoint，便于本地调试；但这种降级不适合依赖进程重启后的真实恢复能力。

## 数据库迁移

在 `backend/` 目录执行：

```bash
alembic upgrade head
alembic revision --autogenerate -m "message"
```

## 测试

在 `backend/` 目录执行：

```bash
python -m pytest
```

后端测试已经覆盖：

- API 路由基础行为
- Conversation / File / AgentRun / Chat Service 的业务编排
- Document indexing 最小处理链路与任务包装器
- 核心 ORM 表注册与基础 Repository 行为

## 约束与说明

- 后端内部 Python 包名保持为 `app`，不要改成 `backend.app.xxx`。
- Graph、LLM、Redis、HTTP Client、Langfuse 在应用启动阶段初始化，请求期间不要重复构建。
- 轻量身份模型默认提供可配置的访客身份，并把不同 `X-API-Key` 派生为彼此隔离的稳定资源拥有者。
- 访客与 API Key 派生身份相关默认值可通过 `GUEST_USER_ID`、`GUEST_USER_NAME`、`API_KEY_USER_ID_PREFIX`、`API_KEY_USER_HASH_SALT` 调整。
- 如需接入完整用户系统，可在保持 Service / Repository / Graph 边界不变的前提下替换当前轻量身份模型。

## 相关文档

- 仓库总览见 [../README.md](../README.md)
- 项目级约束见 [../AGENTS.md](../AGENTS.md)
- 后端补充规则见 [AGENTS.md](./AGENTS.md)
- 项目级 Python 注释规范见 [../skills/ai/python-commenting.md](../skills/ai/python-commenting.md)
- 部署入口见 [../deploy/](../deploy/)
