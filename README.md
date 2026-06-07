# Agent Platform Workspace

这是一个面向二次复用的企业级 Agent 前后端基础脚手架。仓库采用浅层 monorepo 结构，内置：

- `FastAPI + LangGraph + SQLAlchemy async` 后端
- `React + TypeScript + Vite` 前端控制台
- `Docker + Compose + Nginx` 基础部署入口
- 面向所有 AI 助手和人类协作者的 `skills/` 项目级知识目录

## 1. 设计目标

这个仓库面向“拿来做新项目模板”的场景，核心目标是：

- 保持目录边界清晰，避免把前后端、部署和协作规则混在一起
- 提供一套可运行、可测试、可继续扩展的 Agent 平台基础骨架
- 尽量减少本机绑定、个人化痕迹和隐式环境假设
- 同时兼容 AI 协作和人类协作，降低后续维护成本

## 2. 仓库结构

```text
project-root/
├── backend/              # FastAPI + LangGraph + SQLAlchemy async 后端
├── web/                  # React + TypeScript + Vite 前端控制台
├── skills/               # 项目级知识库、协作规范、工程经验沉淀
├── deploy/               # Docker、Compose、Nginx 等部署入口
├── docs/                 # 全栈架构、开发、部署与专题文档
├── scripts/              # 服务整个 monorepo 的项目级脚本
├── AGENTS.md             # 项目级协作规则
├── package.json          # 根目录脚本入口
└── pnpm-workspace.yaml   # pnpm workspace 配置
```

结构约束：

- 顶层直接使用 `backend/`、`web/`、`skills/`、`deploy/`、`docs/`、`scripts/`，不创建 `apps/`
- 后端内部 Python 包名固定为 `app`，内部 import 统一使用 `app.xxx`
- 前端按 `pages/`、`features/`、`shared/` 分层组织
- `skills/` 只承载项目级知识与协作规则，不参与运行时构建

完整结构如下：

```text
agentic-server/
├── AGENTS.md                                      # AI 编码助手入口规则；说明项目结构、强制约束、需要读取哪些 skill
├── README.md                                      # 全栈项目总说明；介绍 backend、web、skills、deploy、docs 的职责和启动方式
├── .gitignore                                     # 全局 Git 忽略规则；忽略 .env、.venv、node_modules、dist、缓存目录等
├── package.json                                   # 根目录脚本入口；用于统一管理 dev:web、dev:backend、build:web 等命令
├── pnpm-workspace.yaml                            # pnpm workspace 配置；用于将 web 纳入前端 workspace 管理
│
├── backend/                                       # 后端服务根目录；包含 FastAPI、LangGraph、数据库、Redis、Langfuse 等后端代码
│   ├── AGENTS.md                                  # 后端专项 AI 规则；可选，用于补充 backend 目录下的 Python 开发约束
│   ├── README.md                                  # 后端说明文档；记录后端启动、测试、数据库迁移、环境变量等说明
│   ├── .env.example                               # 后端环境变量示例；列出 DATABASE_URL、REDIS_URL、LLM_API_KEY 等配置
│   ├── .gitignore                                 # 后端局部忽略规则；可选，用于忽略后端特有缓存、日志、临时文件
│   ├── requirements.txt                           # 后端 Python 依赖清单；适合初期快速安装依赖
│   ├── pyproject.toml                             # 后端 Python 项目配置；可配置 ruff、pytest、mypy、项目元信息等
│   ├── alembic.ini                                # Alembic 数据库迁移配置文件；在 backend 目录下执行迁移命令
│   ├── run.py                                     # 后端本地启动入口；通常执行 uvicorn app.main:app
│   │
│   ├── app/                                       # 后端 Python 主包；内部 import 统一使用 app.xxx
│   │   ├── __init__.py                            # 标记 app 为 Python 包
│   │   ├── main.py                                # FastAPI 应用入口；注册 lifespan、中间件、异常处理器、API 路由
│   │   ├── lifespan.py                            # 应用生命周期管理；初始化和关闭 DB、Redis、LLM、Langfuse、Graph、HTTP Client
│   │   │
│   │   ├── api/                                   # API 接口层；只处理 HTTP 请求、响应、依赖注入和异常映射
│   │   │   ├── __init__.py                        # 标记 api 为 Python 包
│   │   │   ├── dependencies.py                    # FastAPI 依赖注入；提供 get_db、get_graph、get_redis、get_current_user 等
│   │   │   ├── exception_handlers.py              # 全局异常处理器；将 AppException、HTTPException、参数错误等转成统一响应
│   │   │   └── v1/                                # API v1 版本目录；方便未来增加 v2
│   │   │       ├── __init__.py                    # 标记 v1 为 Python 包
│   │   │       ├── health.py                      # 健康检查接口；提供 /health、/ready
│   │   │       ├── chat.py                        # 聊天接口；提供 /v1/chat、/v1/chat/stream
│   │   │       ├── agent.py                       # Agent 控制接口；提供运行状态、暂停、恢复、人类干预等能力
│   │   │       ├── conversations.py               # 会话管理接口；创建、查询、删除、归档会话
│   │   │       └── files.py                       # 文件接口；上传文件、管理 RAG 文档、触发文档处理
│   │   │
│   │   ├── schemas/                               # Pydantic 请求响应模型；定义 API 入参、出参和事件结构
│   │   │   ├── __init__.py                        # 标记 schemas 为 Python 包
│   │   │   ├── common.py                          # 通用 Schema；分页参数、排序参数、时间范围、ID 参数等
│   │   │   ├── response.py                        # 统一响应模型；ApiResponse、PageResponse、StreamEvent
│   │   │   ├── chat.py                            # 聊天相关模型；ChatRequest、ChatResponse、ChatMessage、ChatStreamEvent
│   │   │   ├── agent.py                           # Agent 相关模型；AgentRun 状态、中断恢复、人类审核等
│   │   │   ├── conversation.py                    # 会话相关模型；ConversationCreate、ConversationDetail、ConversationListItem
│   │   │   ├── message.py                         # 消息相关模型；MessageCreate、MessageDetail、MessageRole 等
│   │   │   ├── user.py                            # 用户相关模型；UserInfo、CurrentUser、UserCreate 等
│   │   │   └── file.py                            # 文件相关模型；FileUploadResponse、DocumentInfo、FileStatus 等
│   │   │
│   │   ├── common/                                # 通用基础能力；不依赖具体业务，整个后端可复用
│   │   │   ├── __init__.py                        # 标记 common 为 Python 包
│   │   │   ├── responses.py                       # 统一响应工具；success_response、error_response 等
│   │   │   ├── error_codes.py                     # 统一错误码；定义业务错误、系统错误、外部依赖错误等枚举
│   │   │   ├── exceptions.py                      # 自定义异常；AppException、AuthException、LLMException、GraphException 等
│   │   │   ├── context.py                         # 请求上下文；使用 contextvars 保存 trace_id、request_id、user_id
│   │   │   ├── constants.py                       # 全局常量；默认分页大小、系统用户、默认超时时间等
│   │   │   ├── enums.py                           # 通用枚举；状态枚举、排序方向、环境枚举等
│   │   │   └── pagination.py                      # 分页封装；分页参数解析、分页响应组装
│   │   │
│   │   ├── middlewares/                           # FastAPI / ASGI 中间件；处理 HTTP 横切逻辑
│   │   │   ├── __init__.py                        # 标记 middlewares 为 Python 包
│   │   │   ├── request_context.py                 # 请求上下文中间件；生成或继承 X-Trace-Id、X-Request-Id
│   │   │   ├── access_log.py                      # 访问日志中间件；记录 method、path、status_code、cost_ms、trace_id
│   │   │   ├── audit_log.py                       # 基础审计中间件；记录用户、IP、路径、操作结果等基础审计信息
│   │   │   ├── timing.py                          # 请求耗时中间件；写入 X-Process-Time-Ms 响应头
│   │   │   └── cors.py                            # CORS 配置封装；集中注册跨域规则
│   │   │
│   │   ├── core/                                  # 后端核心配置；只放配置、安全、日志等基础设施
│   │   │   ├── __init__.py                        # 标记 core 为 Python 包
│   │   │   ├── config.py                          # 配置管理；使用 pydantic-settings 从环境变量读取配置
│   │   │   ├── logging.py                         # 日志配置；设置日志格式、等级、trace_id 注入等
│   │   │   ├── security.py                        # 安全工具；API Key、JWT、密码散列、权限校验等
│   │   │   └── app_factory.py                     # 应用工厂；可选，用于封装 create_app()，保持 main.py 简洁
│   │   │
│   │   ├── db/                                    # 数据库层；SQLAlchemy 2.x async + Repository Pattern
│   │   │   ├── __init__.py                        # 标记 db 为 Python 包
│   │   │   ├── base.py                            # SQLAlchemy DeclarativeBase；配置 metadata naming_convention
│   │   │   ├── session.py                         # 数据库会话；创建 AsyncEngine、AsyncSessionLocal、get_db_session
│   │   │   ├── mixins.py                          # ORM 通用字段；UUID 主键、created_at、updated_at、deleted_at
│   │   │   ├── transaction.py                     # 事务工具；封装事务上下文，辅助 Service 层控制事务
│   │   │   ├── models/                            # ORM 模型目录；只定义数据库表结构
│   │   │   │   ├── __init__.py                    # 统一导入所有模型；供 Alembic autogenerate 识别
│   │   │   │   ├── user.py                        # 用户表；保存用户基础信息
│   │   │   │   ├── api_key.py                     # API Key 表；保存用户或系统级 API Key 及状态
│   │   │   │   ├── conversation.py                # 会话表；保存 Agent 对话会话信息
│   │   │   │   ├── message.py                     # 消息表；保存用户消息、AI 消息、系统消息、工具消息等
│   │   │   │   ├── agent_run.py                   # Agent 运行记录表；记录每次 graph invoke 或 stream 执行
│   │   │   │   ├── tool_call.py                   # 工具调用记录表；记录工具名称、参数、结果、耗时、错误等
│   │   │   │   ├── audit_log.py                   # 审计日志表；记录用户行为、系统行为、安全敏感操作
│   │   │   │   ├── file.py                        # 文件表；保存上传文件的元信息、路径、状态、所属用户
│   │   │   │   └── document.py                    # RAG 文档表；保存文档切片、索引状态、来源文件等信息
│   │   │   └── repositories/                      # 数据访问层；封装 SQL 查询，不写业务逻辑，不主动 commit
│   │   │       ├── __init__.py                    # 标记 repositories 为 Python 包
│   │   │       ├── base.py                        # BaseRepository；封装通用 get、list、create、update、delete 方法
│   │   │       ├── user_repo.py                   # 用户 Repository；封装用户查询和写入
│   │   │       ├── conversation_repo.py           # 会话 Repository；封装会话查询、创建、软删除
│   │   │       ├── message_repo.py                # 消息 Repository；封装消息写入、历史查询、分页查询
│   │   │       ├── agent_run_repo.py              # AgentRun Repository；封装运行记录创建、更新状态、查询详情
│   │   │       ├── tool_call_repo.py              # ToolCall Repository；封装工具调用记录写入和查询
│   │   │       ├── audit_log_repo.py              # AuditLog Repository；封装审计日志写入和检索
│   │   │       └── file_repo.py                   # File Repository；封装文件元数据查询、状态更新
│   │   │
│   │   ├── integrations/                          # 外部基础设施集成；封装第三方依赖，避免业务层直接耦合具体客户端
│   │   │   ├── __init__.py                        # 标记 integrations 为 Python 包
│   │   │   ├── redis.py                           # Redis 客户端；创建连接池、关闭连接、处理 Redis 降级
│   │   │   ├── cache.py                           # 缓存封装；get、set、delete、TTL、namespace 等
│   │   │   ├── rate_limit.py                      # 限流封装；基于 Redis 或内存实现简单限流策略
│   │   │   ├── distributed_lock.py                # 分布式锁；基于 Redis 实现锁获取、释放、超时保护
│   │   │   ├── http_client.py                     # HTTP Client；统一创建和关闭 httpx.AsyncClient
│   │   │   ├── object_storage.py                  # 对象存储预留；S3、MinIO、OSS 等上传下载封装
│   │   │   └── queue.py                           # 队列预留；MQ、任务队列、Redis Stream 等封装
│   │   │
│   │   ├── observability/                         # 可观测性模块；负责 trace、metrics、Langfuse、日志上下文等
│   │   │   ├── __init__.py                        # 标记 observability 为 Python 包
│   │   │   ├── langfuse.py                        # Langfuse 客户端；初始化、flush、shutdown、降级处理
│   │   │   ├── tracing.py                         # Trace 封装；创建 span、读取 trace_id、关联外部观测系统
│   │   │   ├── langchain_callbacks.py             # LangChain / LangGraph callback handler 封装
│   │   │   ├── metrics.py                         # 指标封装；Prometheus 或自定义指标预留
│   │   │   ├── decorators.py                      # 观测装饰器；trace_operation、observe_node 等
│   │   │   └── log_context.py                     # 日志上下文；将 trace_id、request_id、user_id 注入日志
│   │   │
│   │   ├── audit/                                 # 审计领域模块；记录“谁在什么时候做了什么”
│   │   │   ├── __init__.py                        # 标记 audit 为 Python 包
│   │   │   ├── schemas.py                         # 审计事件模型；AuditEvent、AuditActor、AuditResource 等
│   │   │   ├── service.py                         # 审计服务；提供 record_audit_event() 等统一入口
│   │   │   ├── writer.py                          # 审计写入器；写 DB、Redis Stream、MQ、文件等策略
│   │   │   └── enums.py                           # 审计枚举；AuditAction、AuditResult、AuditResourceType 等
│   │   │
│   │   ├── llms/                                  # LLM 实例管理；统一管理 ChatModel、Embedding、Rerank、Fallback
│   │   │   ├── __init__.py                        # 标记 llms 为 Python 包
│   │   │   ├── factory.py                         # LLM 工厂；根据配置创建 OpenAI、DeepSeek、Qwen、Ollama 等模型
│   │   │   ├── chat.py                            # ChatModel 创建逻辑；封装 ChatOpenAI 或兼容 OpenAI 的模型
│   │   │   ├── embeddings.py                      # Embedding 模型创建逻辑；用于 RAG 文档向量化
│   │   │   ├── rerank.py                          # Rerank 模型预留；用于检索结果重排序
│   │   │   └── fallback.py                        # 模型降级策略；主模型失败时切换备用模型或 mock 模式
│   │   │
│   │   ├── graph/                                 # LangGraph 编排层；只负责 Agent 状态、节点、路由、图构建
│   │   │   ├── __init__.py                        # 标记 graph 为 Python 包
│   │   │   ├── state.py                           # AgentState 定义；声明 messages、user_id、conversation_id、metadata 等状态
│   │   │   ├── builder.py                         # Graph 构建器；组装 StateGraph、节点、条件边、checkpointer 并 compile
│   │   │   ├── routing.py                         # 条件路由；判断是否调用工具、是否结束、是否进入人工审核
│   │   │   ├── checkpoint.py                      # Checkpointer 封装；SqliteSaver、PostgresSaver 等持久化检查点配置
│   │   │   ├── store.py                           # 长期记忆 Store；跨线程、跨会话的长期记忆存储封装
│   │   │   ├── nodes/                             # LangGraph 节点目录；每个节点负责一个明确动作
│   │   │   │   ├── __init__.py                    # 标记 nodes 为 Python 包
│   │   │   │   ├── agent.py                       # 主 Agent 节点；读取 messages，调用 LLM 生成回复或 tool_calls
│   │   │   │   ├── retriever.py                   # RAG 检索节点；根据问题检索文档、知识库或向量库
│   │   │   │   ├── tool_executor.py               # 工具执行节点；执行 tool_calls，可封装 LangGraph ToolNode
│   │   │   │   ├── summarize.py                   # 总结节点；对长对话进行摘要，压缩上下文
│   │   │   │   ├── memory.py                      # 记忆节点；读取或写入长期记忆
│   │   │   │   └── human_review.py                # 人类审核节点；处理中断、审批、人工确认等场景
│   │   │   ├── tools/                             # Agent 可调用工具集合；供 LLM tool calling 使用
│   │   │   │   ├── __init__.py                    # 标记 tools 为 Python 包
│   │   │   │   ├── search.py                      # 搜索工具；Tavily、DuckDuckGo、SerpAPI 等预留
│   │   │   │   ├── database.py                    # 数据库工具；安全封装查询能力，禁止直接拼接 SQL
│   │   │   │   ├── calculator.py                  # 计算工具；处理确定性数学计算
│   │   │   │   ├── browser.py                     # 浏览器工具；网页读取、内容提取等预留
│   │   │   │   └── file.py                        # 文件工具；读取上传文件、解析文档内容等
│   │   │   └── prompts/                           # Prompt 管理目录；集中存放系统提示词和节点专用 Prompt
│   │   │       ├── __init__.py                    # 标记 prompts 为 Python 包
│   │   │       ├── system.py                      # 系统提示词；定义 Agent 基础行为、边界、安全约束
│   │   │       ├── chat.py                        # 聊天 Prompt；普通对话 Agent 使用
│   │   │       ├── rag.py                         # RAG Prompt；检索增强回答使用
│   │   │       ├── tool_use.py                    # 工具调用 Prompt；约束工具选择和参数生成
│   │   │       └── human_review.py                # 人类审核 Prompt；解释为什么需要人工确认
│   │   │
│   │   ├── services/                              # 业务服务层；负责编排业务逻辑、事务边界和跨模块协作
│   │   │   ├── __init__.py                        # 标记 services 为 Python 包
│   │   │   ├── graph_runner.py                    # Graph 执行服务；封装 graph.invoke、graph.ainvoke、graph.astream_events
│   │   │   ├── chat_service.py                    # 聊天服务；协调会话、消息、Graph 执行、审计记录
│   │   │   ├── conversation_service.py            # 会话服务；创建、查询、删除、归档会话
│   │   │   ├── message_service.py                 # 消息服务；消息写入、历史消息查询、消息状态维护
│   │   │   ├── agent_run_service.py               # Agent 运行服务；创建运行记录、更新状态、关联 trace
│   │   │   ├── tool_call_service.py               # 工具调用服务；记录工具调用输入输出、错误和耗时
│   │   │   ├── file_service.py                    # 文件服务；处理上传、校验、状态更新、文档解析触发
│   │   │   └── user_service.py                    # 用户服务；用户信息、API Key、权限相关逻辑
│   │   │
│   │   ├── tasks/                                 # 异步任务预留；未来可接 Celery、RQ、Arq、后台任务等
│   │   │   ├── __init__.py                        # 标记 tasks 为 Python 包
│   │   │   ├── document_indexing.py               # 文档索引任务；文件解析、切片、embedding、写入向量库
│   │   │   ├── cleanup.py                         # 清理任务；清理临时文件、过期会话、历史运行记录等
│   │   │   └── audit_flush.py                     # 审计刷写任务；批量写入审计日志或转发到外部系统
│   │   │
│   │   └── utils/                                 # 后端工具函数；只放无业务状态的小工具，避免变成垃圾桶
│   │       ├── __init__.py                        # 标记 utils 为 Python 包
│   │       ├── ids.py                             # ID 工具；UUID、短 ID、雪花 ID 等生成方法
│   │       ├── time.py                            # 时间工具；UTC 时间、时间格式化、时间范围计算
│   │       ├── json.py                            # JSON 工具；安全序列化、特殊对象编码
│   │       ├── hashing.py                         # 哈希工具；签名、摘要、密码散列辅助能力
│   │       └── text.py                            # 文本工具；截断、清洗、token 估算等
│   │
│   ├── migrations/                                # Alembic 数据库迁移目录
│   │   ├── env.py                                 # Alembic 环境配置；读取 settings.DATABASE_URL，绑定 Base.metadata
│   │   ├── script.py.mako                         # Alembic 迁移脚本模板；生成 revision 文件时使用
│   │   ├── README                                 # Alembic 目录说明；可记录迁移命令和注意事项
│   │   └── versions/                              # 迁移版本目录；存放每次 revision 生成的迁移脚本
│   │       └── .gitkeep                           # 保留空目录；避免 versions 目录未提交到 Git
│   │
│   ├── tests/                                     # 后端测试目录
│   │   ├── __init__.py                            # 标记 tests 为 Python 包；可选
│   │   ├── conftest.py                            # pytest 公共 fixture；test_client、db_session、mock_llm 等
│   │   ├── api/                                   # API 层测试；测试 health、chat、agent、conversation 等接口
│   │   ├── services/                              # Service 层测试；测试业务逻辑和事务边界
│   │   ├── db/                                    # 数据库层测试；测试 ORM 模型和 Repository
│   │   ├── graph/                                 # LangGraph 层测试；测试 graph 构建、节点、路由
│   │   ├── common/                                # 通用能力测试；测试响应格式、错误码、异常处理
│   │   ├── middlewares/                           # 中间件测试；测试 trace_id、access log、timing 等
│   │   └── integrations/                          # 外部集成测试；测试 Redis、Cache、HTTP Client 等封装
│   │
│   └── scripts/                                   # 后端脚本目录；只放后端相关的本地开发或运维脚本
│       ├── init_db.py                             # 初始化数据库脚本；创建基础数据或检查数据库连通性
│       ├── dev_seed.py                            # 开发环境造数脚本；生成测试用户、会话、消息等
│       ├── check_env.py                           # 后端环境变量检查脚本；验证必要配置是否存在
│       ├── create_admin.py                        # 创建管理员用户脚本；可选
│       └── clear_cache.py                         # 清理 Redis 缓存脚本；可选
│
├── web/                                           # 前端服务根目录；React + TypeScript + Vite + Tailwind + shadcn/ui
│   ├── AGENTS.md                                  # 前端专项 AI 规则；可选，用于补充 web 目录下的开发约束
│   ├── README.md                                  # 前端说明文档；记录前端启动、构建、目录结构、接口约定
│   ├── index.html                                 # Vite HTML 入口文件；挂载 React 根节点
│   ├── package.json                               # 前端依赖和脚本；dev、build、preview、lint 等
│   ├── pnpm-lock.yaml                             # pnpm 锁文件；pnpm install 后生成
│   ├── tsconfig.json                              # TypeScript 主配置；配置 JSX、路径别名、严格模式等
│   ├── tsconfig.node.json                         # Node/Vite TypeScript 配置；用于 vite.config.ts 等 Node 环境文件
│   ├── vite.config.ts                             # Vite 配置；配置 React 插件、路径别名、开发代理等
│   ├── components.json                            # shadcn/ui 配置；定义组件目录、别名、样式方案等
│   ├── tailwind.config.ts                         # Tailwind CSS 配置；扫描路径、主题扩展、插件配置
│   ├── postcss.config.js                          # PostCSS 配置；加载 Tailwind 和 autoprefixer
│   ├── eslint.config.js                           # ESLint 配置；前端代码质量检查规则
│   ├── .env.example                               # 前端环境变量示例；VITE_API_BASE_URL、VITE_API_PREFIX 等
│   │
│   ├── public/                                    # 静态资源目录；文件原样复制到构建产物
│   │   └── favicon.svg                            # 浏览器图标
│   │
│   └── src/                                       # 前端源码目录
│       ├── main.tsx                               # React 应用入口；创建 root，挂载 App
│       ├── App.tsx                                # App 根组件；通常挂载 RouterProvider 或全局布局
│       ├── vite-env.d.ts                          # Vite 类型声明；提供 import.meta.env 等类型
│       │
│       ├── app/                                   # 前端应用级配置
│       │   ├── router.tsx                         # React Router 路由定义；声明 /chat、/conversations 等页面
│       │   ├── providers.tsx                      # 全局 Provider；QueryClientProvider、ThemeProvider 等
│       │   └── query-client.ts                    # TanStack Query Client 配置；统一缓存、重试、错误策略
│       │
│       ├── pages/                                 # 页面级组件；一个页面对应一个路由
│       │   ├── chat/                              # 聊天页面目录
│       │   │   ├── ChatPage.tsx                   # Agent 聊天主页面；组合消息列表、输入框、流式输出
│       │   │   └── components/                    # 聊天页面内部组件；只服务 ChatPage
│       │   │       ├── ChatInput.tsx              # 聊天输入框；负责输入、快捷键、发送按钮状态
│       │   │       ├── MessageList.tsx            # 消息列表；渲染用户消息、AI 消息、工具消息
│       │   │       ├── MessageBubble.tsx          # 单条消息气泡；根据 role 显示不同样式
│       │   │       └── StreamMessage.tsx          # 流式消息展示；处理增量文本、光标、loading 状态
│       │   ├── conversations/                     # 会话页面目录
│       │   │   ├── ConversationListPage.tsx       # 会话列表页；展示历史会话、搜索、分页
│       │   │   └── ConversationDetailPage.tsx     # 会话详情页；展示单个会话的消息和元信息
│       │   ├── agent-runs/                        # Agent 运行记录页面目录
│       │   │   ├── AgentRunsPage.tsx              # Agent 运行列表页；展示运行状态、模型、耗时、trace
│       │   │   └── AgentRunDetailPage.tsx         # Agent 运行详情页；展示节点执行、工具调用、错误信息
│       │   ├── files/                             # 文件管理页面目录
│       │   │   └── FilesPage.tsx                  # 文件页面；上传文件、查看解析状态、管理 RAG 文档
│       │   ├── settings/                          # 设置页面目录
│       │   │   └── SettingsPage.tsx               # 设置页；配置 API 地址、模型偏好、本地 UI 设置等
│       │   └── not-found/                         # 404 页面目录
│       │       └── NotFoundPage.tsx               # 404 页面；路由未匹配时显示
│       │
│       ├── features/                              # 前端业务功能模块；按业务领域封装 API、hooks、types
│       │   ├── chat/                              # 聊天业务模块
│       │   │   ├── api.ts                         # 聊天 API；封装 /v1/chat、/v1/chat/stream 调用
│       │   │   ├── hooks.ts                       # 聊天 hooks；useChat、useStreamChat 等
│       │   │   ├── types.ts                       # 聊天类型；ChatMessage、ChatRequest、ChatResponse 等
│       │   │   └── utils.ts                       # 聊天工具函数；消息转换、流式文本拼接等
│       │   ├── conversations/                     # 会话业务模块
│       │   │   ├── api.ts                         # 会话 API；创建、查询、删除会话
│       │   │   ├── hooks.ts                       # 会话 hooks；useConversations、useConversationDetail 等
│       │   │   └── types.ts                       # 会话类型；Conversation、ConversationListItem 等
│       │   ├── agent-runs/                        # Agent 运行记录业务模块
│       │   │   ├── api.ts                         # AgentRun API；查询运行列表和详情
│       │   │   ├── hooks.ts                       # AgentRun hooks；useAgentRuns、useAgentRunDetail 等
│       │   │   └── types.ts                       # AgentRun 类型；运行状态、节点信息、工具调用信息
│       │   └── files/                             # 文件业务模块
│       │       ├── api.ts                         # 文件 API；上传、查询、删除文件
│       │       ├── hooks.ts                       # 文件 hooks；useFiles、useUploadFile 等
│       │       └── types.ts                       # 文件类型；FileInfo、UploadResponse、DocumentStatus 等
│       │
│       ├── shared/                                # 前端公共能力；跨页面、跨业务模块复用
│       │   ├── api/                               # 前端 API 基础封装
│       │   │   ├── client.ts                      # fetch 客户端；统一 baseUrl、headers、错误处理、request_id
│       │   │   ├── endpoints.ts                   # API endpoint 常量；集中维护后端接口路径
│       │   │   ├── errors.ts                      # API 错误处理；将后端错误响应转成前端异常或提示
│       │   │   └── stream.ts                      # 流式请求封装；使用 fetch ReadableStream 处理 SSE / chunk
│       │   ├── components/                        # 前端通用组件
│       │   │   ├── ui/                            # shadcn/ui 风格基础组件
│       │   │   │   ├── button.tsx                 # Button 组件；统一按钮样式和变体
│       │   │   │   ├── input.tsx                  # Input 组件；统一输入框样式
│       │   │   │   ├── textarea.tsx               # Textarea 组件；用于多行输入和聊天框
│       │   │   │   ├── card.tsx                   # Card 组件；用于信息块、页面区块
│       │   │   │   ├── badge.tsx                  # Badge 组件；用于状态标签、类型标签
│       │   │   │   ├── scroll-area.tsx            # ScrollArea 组件；用于消息列表、详情面板滚动区域
│       │   │   │   └── separator.tsx              # Separator 组件；用于分割线
│       │   │   ├── layout/                        # 布局组件
│       │   │   │   ├── AppLayout.tsx              # 应用主布局；组合 Sidebar、Header、内容区域
│       │   │   │   ├── Sidebar.tsx                # 侧边栏；导航 Chat、Conversations、Agent Runs、Files、Settings
│       │   │   │   └── Header.tsx                 # 顶部栏；展示标题、环境、用户入口等
│       │   │   └── feedback/                      # 反馈组件
│       │   │       ├── LoadingState.tsx           # 加载状态组件；统一 loading 展示
│       │   │       ├── EmptyState.tsx             # 空状态组件；列表为空或暂无数据时展示
│       │   │       └── ErrorState.tsx             # 错误状态组件；请求失败或页面异常时展示
│       │   ├── hooks/                             # 通用 hooks
│       │   │   ├── useBoolean.ts                  # 布尔状态 hook；open/close/toggle 等
│       │   │   └── useDebounce.ts                 # 防抖 hook；搜索输入、自动保存等场景
│       │   ├── lib/                               # 通用库函数
│       │   │   ├── cn.ts                          # className 合并工具；通常基于 clsx + tailwind-merge
│       │   │   ├── storage.ts                     # localStorage / sessionStorage 封装
│       │   │   ├── date.ts                        # 日期格式化、相对时间等工具
│       │   │   └── id.ts                          # 前端 ID 工具；生成 request_id、临时消息 ID 等
│       │   ├── types/                             # 全局类型
│       │   │   ├── api.ts                         # ApiResponse、PageResponse、统一错误结构等
│       │   │   └── common.ts                      # 通用类型；ID、时间、状态、选项等
│       │   └── constants/                         # 前端常量
│       │       ├── routes.ts                      # 前端路由常量；避免路径散落在组件中
│       │       └── query-keys.ts                  # TanStack Query keys；统一管理缓存 key
│       │
│       ├── styles/                                # 全局样式目录
│       │   └── globals.css                        # Tailwind 全局样式；引入 base、components、utilities 和 CSS 变量
│       │
│       └── assets/                                # 前端打包资源；会被 Vite 处理
│           └── logo.svg                           # 项目 Logo；用于 Header、登录页或 favicon 备用
│
├── skills/                                        # 面向所有 AI 助手和人类协作者的项目级知识目录；不参与 backend 或 web 运行时构建
│   ├── README.md                                  # skills 总说明；解释 skill 的命名、用途、使用方式
│   │
│   ├── ai/                                        # 项目级 AI 协作入口资料
│   │   └── python-commenting.md                   # Python 注释入口；供所有 AI 助手和人类协作者快速引用
│   │
│   ├── architecture/                              # 架构知识目录；沉淀前后端与全栈结构说明
│   │   ├── backend-architecture.md                # 后端架构说明
│   │   ├── frontend-architecture.md               # 前端架构说明
│   │   └── fullstack-architecture.md              # 全栈结构关系说明
│   │
│   ├── agent/                                     # Agent 领域知识目录
│   │   ├── langgraph.md                           # LangGraph 相关说明
│   │   ├── memory.md                              # Agent memory 相关说明
│   │   ├── prompts.md                             # Prompt 设计说明
│   │   └── tools.md                               # Tool calling 相关说明
│   │
│   ├── operations/                                # 运维与可观测性知识目录
│   │   ├── deployment.md                          # 部署实践说明
│   │   ├── observability.md                       # 可观测性实践说明
│   │   └── troubleshooting.md                     # 常见排障说明
│   │
│   ├── python-commenting/                         # Python 注释与 Docstring 规范技能
│   │   └── SKILL.md                               # 详细说明 Python 注释规范、docstring 规范、自检清单
│   │
│   ├── project-overview-docenerator/              # 历史项目说明文档生成目录；仅为兼容旧引用保留
│   │   ├── SKILL.md                               # 旧版项目说明文档生成规范
│   │   └── template/                              # 旧版模板目录
│   │       └── template.md                        # 旧版项目说明模板
│   │
│   ├── project-overview-generator/                # 项目概览 / 架构文档生成技能
│   │   ├── SKILL.md                               # 说明如何读取项目、生成项目概览、模块说明和架构文档
│   │   └── templates/                             # 当前 skill 使用的模板
│   │       ├── project-overview.md                # 项目概览文档模板
│   │       └── architecture-overview.md           # 架构概览文档模板
│   │
│   ├── backend-development/                       # 后端开发规范技能；可选
│   │   └── SKILL.md                               # 后端分层、事务、Repository、异常、响应、配置等规范
│   │
│   ├── frontend-development/                      # 前端开发规范技能；可选
│   │   └── SKILL.md                               # React、TypeScript、shadcn/ui、路由、状态管理等规范
│   │
│   ├── testing/                                   # 测试规范技能；可选
│   │   └── SKILL.md                               # 后端 pytest、前端测试、mock、集成测试等规范
│   │
│   └── code-review/                               # 代码审查规范技能；可选
│       └── SKILL.md                               # 代码审查清单；安全、性能、可维护性、注释、测试覆盖等
│
├── deploy/                                        # 全栈部署配置目录
│   ├── docker/                                    # Docker 镜像构建文件
│   │   ├── backend.Dockerfile                     # 后端 Dockerfile；构建 FastAPI 服务镜像
│   │   └── web.Dockerfile                         # 前端 Dockerfile；构建 Vite 静态资源或 Nginx 镜像
│   ├── compose/                                   # Docker Compose 编排文件
│   │   ├── docker-compose.yml                     # 标准 compose；包含 backend、web、postgres、redis
│   │   └── docker-compose.dev.yml                 # 开发环境 compose；支持热更新、挂载代码、开发端口
│   └── nginx/                                     # Nginx 配置
│       └── nginx.conf                             # 反向代理配置；/v1 转发到 backend，/ 转发到 web
│
├── docs/                                          # 全局项目文档
│   ├── architecture.md                            # 总体架构文档；说明 backend、web、skills、deploy 的关系
│   ├── backend.md                                 # 后端文档；启动、测试、迁移、分层说明
│   ├── web.md                                     # 前端文档；技术栈、启动、目录结构、组件规范
│   ├── development.md                             # 开发说明文档；补充根目录与分目录启动方式
│   ├── api_response.md                            # 统一响应说明；success、code、message、data、trace_id
│   ├── error_codes.md                             # 错误码文档；错误码分段、含义、维护规则
│   ├── database.md                                # 数据库文档；模型说明、迁移命令、Repository 约定
│   ├── observability.md                           # 可观测性文档；trace_id、Langfuse、日志、指标说明
│   ├── audit.md                                   # 审计文档；审计事件、字段、写入策略、查询场景
│   └── deployment.md                              # 部署文档；Docker Compose、Nginx、环境变量、生产部署注意事项
│
└── scripts/                                       # 项目级脚本目录；服务整个 monorepo
    ├── dev.ps1                                    # Windows 一键开发启动脚本；可同时启动 backend 和 web
    ├── dev.sh                                     # Unix/macOS/Linux 一键开发启动脚本
    └── check_env.py                               # 全局环境检查脚本；检查 backend 和 web 的必要环境变量
```

## 3. 已提供的基础能力

后端：

- 健康检查：`GET /health`、`GET /ready`
- 聊天接口：`POST /v1/chat`、`POST /v1/chat/stream`
- 会话管理：创建、列表、详情、消息列表、删除
- 文件管理：列表、详情、上传、下载、删除
- Agent Run：列表、详情、状态、中断、恢复
- 基础持久化链路：conversation、message、agent run、tool call、audit log
- 最小文档索引链路：文本类文件上传后可登记并索引到 `documents`

前端：

- `/chat`
- `/conversations`
- `/conversations/:conversationId`
- `/agent-runs`
- `/agent-runs/:runId`
- `/files`
- `/settings`
- 已接入后端聊天、会话、运行记录、文件管理接口

部署：

- `backend` / `web` 独立 Dockerfile
- 生产风格与开发风格 Compose 配置
- Nginx 统一入口、SPA 路由回退与 `/v1/` 反向代理
- 基础健康检查与容器依赖顺序

## 4. 快速开始

运行时建议：

- Python `3.11+`
- Node `18.18+`
- pnpm `9.15+`

根目录常用命令：

```bash
pnpm dev:web
pnpm build:web
pnpm lint:web
pnpm dev:backend
pnpm test:backend
pnpm check:env
pnpm compose:up
pnpm compose:dev
pnpm compose:down
```

后端启动：

```bash
cd backend
python run.py
```

或：

```bash
cd backend
uvicorn app.main:app --reload
```

前端启动：

```bash
cd web
pnpm install
pnpm dev
```

后端迁移：

```bash
cd backend
alembic revision --autogenerate -m "message"
alembic upgrade head
```

## 5. Docker / Compose

生产风格本地联调：

```bash
cd deploy/compose
docker compose up --build
```

或：

```bash
pnpm compose:up
```

开发风格联调：

```bash
cd deploy/compose
docker compose -f docker-compose.dev.yml up --build
```

或：

```bash
pnpm compose:dev
```

默认访问入口：

- `http://localhost/`：Nginx 入口
- `http://localhost/v1/...`：通过 Nginx 访问后端 API
- `http://localhost:8000`：直接访问 FastAPI
- `http://localhost:5173`：开发版 Compose 的 Vite 服务

## 6. 协作入口

开始修改前，优先阅读：

- [AGENTS.md](./AGENTS.md)
- [backend/AGENTS.md](./backend/AGENTS.md)
- [web/AGENTS.md](./web/AGENTS.md)
- [skills/README.md](./skills/README.md)
- [skills/ai/python-commenting.md](./skills/ai/python-commenting.md)

扩展阅读：

- [backend/README.md](./backend/README.md)
- [web/README.md](./web/README.md)
- [docs/architecture.md](./docs/architecture.md)
- [docs/development.md](./docs/development.md)
- [docs/deployment.md](./docs/deployment.md)

## 7. 结构说明补充

当前仓库更关注“结构可复用性”而不是单一业务实现的完整度。  
继续扩展时，建议优先保持以下稳定性：

- `backend/`、`web/`、`deploy/`、`docs/`、`skills/` 的边界不要互相侵入
- 后端内部持续保持 `app.xxx` import 约定
- 前端持续保持 `pages/`、`features/`、`shared/` 三层边界
- 目录结构、启动命令、部署入口变动时同步更新 README 和 `docs/`
