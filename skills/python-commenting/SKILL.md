# Python 注释与 Docstring 规范

本规范适用于 `backend/` 下所有 Python 代码。

目标不是让代码充满注释，而是让关键代码具备可维护性、可审计性和可协作性。

本项目统一使用 Google Style Docstring。

## 总原则

1. 优先写清晰代码，再用注释补充上下文。
2. 注释解释 Why，不重复 What。
3. 公开模块、公开类、公开函数必须写 docstring。
4. 复杂私有函数、复杂分支、外部系统调用、事务边界、降级策略必须写注释或 docstring。
5. 修改代码行为时，必须同步更新已有 docstring。
6. 删除过期注释，禁止保留和代码不一致的说明。
7. 不写无意义注释。
8. 注释应该帮助后续维护者理解业务意图、设计取舍、边界条件和风险点。
9. 所有的注释应该用中文编写

## 修改已有代码时优先补什么

1. 先检查已有 docstring 是否还和当前行为一致，不一致就先修正。
2. 优先补状态流转、恢复逻辑、事务边界、降级策略，不要先补表层流程描述。
3. 如果一个函数跨越多个层级概念，例如“持久化 + graph 恢复 + 前端协议兼容”，必须解释这样做的原因。
4. 行内注释只放在维护者最容易误判的分支附近，避免把整段代码注释成自然语言。

## 模块级 Docstring

以下模块必须写模块级 docstring：

* `app/main.py`
* `app/lifespan.py`
* `app/core/*.py`
* `app/common/*.py`
* `app/api/exception_handlers.py`
* `app/middlewares/*.py`
* `app/db/session.py`
* `app/db/base.py`
* `app/integrations/*.py`
* `app/observability/*.py`
* `app/services/*.py`
* `app/graph/*.py`
* `app/graph/nodes/*.py`

模块级 docstring 应说明：

1. 当前模块负责什么。
2. 当前模块不负责什么。
3. 与其他层的关系。
4. 重要约束或设计取舍。

示例：

```python
"""LangGraph 构建模块。

本模块负责组装 AgentState、节点、条件路由和 checkpointer，并返回
编译后的 LangGraph graph 实例。

约束：
- 不在请求期间重复编译 graph。
- 不在本模块中读取 HTTP 请求对象。
- 不在本模块中直接创建 LLM，LLM 应由 lifespan 初始化后注入。
"""
```

## 类 Docstring

以下类型的类必须写 class docstring：

* Service
* Repository
* Middleware
* Writer
* Factory
* Client
* Graph 相关类
* 复杂 ORM Model
* 复杂 Pydantic Schema

class docstring 应说明：

1. 类的职责。
2. 所属层级。
3. 是否管理事务。
4. 是否持有外部资源。
5. 调用方需要注意的边界。

示例：

```python
class ConversationService:
    """会话业务服务。

    负责会话创建、查询、删除等业务编排。
    本类控制事务边界，可以调用多个 Repository。
    API 层不应直接访问 Repository。
    """
```

## 函数 Docstring

以下函数必须写 docstring：

* API dependency 函数
* Service 层公开方法
* Repository 层公开方法
* Middleware dispatch 方法
* LangGraph node 函数
* LangGraph routing 函数
* LLM factory 函数
* Redis、HTTP Client、Langfuse 等外部集成函数
* 会产生副作用的函数
* 包含复杂条件判断的函数

函数 docstring 应根据需要包含：

* Args
* Returns
* Raises
* Side Effects
* Notes

示例：

```python
async def create_conversation(user_id: str, title: str | None = None) -> Conversation:
    """创建一个新的会话。

    该方法只负责创建会话实体，不负责写入首条消息。
    事务边界由 Service 层控制，Repository 层不主动 commit。

    Args:
        user_id: 当前用户 ID。
        title: 会话标题。如果为空，后续可由总结任务自动生成。

    Returns:
        创建完成但尚未提交事务的 Conversation ORM 对象。

    Raises:
        DatabaseException: 当数据库写入失败时抛出。
    """
```

## FastAPI 专项规范

### API Router

API 路由函数 docstring 应说明接口语义，不重复路径和 HTTP 方法。

```python
@router.post("/chat")
async def chat(request: ChatRequest) -> ApiResponse[ChatResponse]:
    """执行一次非流式 Agent 对话。

    该接口适用于普通请求-响应场景。
    流式聊天请使用 `/chat/stream`。
    """
```

### Dependencies

Dependency 函数必须说明资源来源。

```python
def get_graph(request: Request):
    """从 FastAPI app.state 获取启动期编译好的 LangGraph 实例。

    Graph 在 lifespan 中初始化，禁止在请求期间重复 build。
    """
```

### Exception Handler

异常处理器必须说明异常到响应的映射规则。

```python
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """将项目内 AppException 转换为统一错误响应。"""
```

## LangGraph 专项规范

LangGraph 代码必须更重视注释，因为图编排逻辑不是线性的。

### State

`state.py` 中每个核心状态字段都要说明用途。

```python
class AgentState(TypedDict):
    """Agent 图运行期间共享的状态。"""

    messages: Annotated[list[AnyMessage], add_messages]
    """当前线程的消息列表，由 LangGraph message reducer 负责合并。"""

    conversation_id: str | None
    """当前会话 ID。为空时表示尚未持久化会话。"""

    metadata: dict[str, Any]
    """运行期元信息，例如 trace_id、user_id、model、tool_call_count。"""
```

### Node

每个 node 必须说明：

1. 读取哪些 state 字段。
2. 写入哪些 state 字段。
3. 是否调用外部系统。
4. 是否可能抛出业务异常。
5. 是否允许被重试。

示例：

```python
async def agent_node(state: AgentState) -> dict[str, Any]:
    """调用 LLM 生成下一步回复。

    Reads:
        messages: 当前对话上下文。
        metadata: trace_id、user_id、model 等运行时信息。

    Writes:
        messages: 追加 AIMessage。

    Side Effects:
        可能调用外部 LLM API。
        可能写入 Langfuse observation。

    Raises:
        LLMException: 当模型调用失败且无法降级时抛出。
    """
```

### 人机交互 / 恢复节点

如果节点涉及 `interrupt`、`resume`、checkpoint、表单补参，额外说明：

1. 补参值从哪里读取，例如 `human_input` 或 `metadata.resume_payload`。
2. 合并完成后是否会清理一次性字段，避免重复消费。
3. 为什么当前分支返回“待补参”而不是直接抛异常。
4. 完成态是否需要清理 `pending_human_input`、`interrupt_source` 等中断痕迹。

示例：

```python
async def resume_merge_node(state: AgentState) -> dict[str, Any]:
    """合并用户补参并清理一次性恢复载荷。

    Reads:
        human_input: 当前恢复动作提交的结构化表单值。
        metadata: 兼容旧版恢复协议时使用的补参载荷。

    Writes:
        origin_text / destination_text / travel_mode: 合并后的最新槽位。
        human_input: 清空，避免同一份表单被后续节点重复消费。

    Notes:
        补参失败属于可恢复业务分支，应通过缺失字段和校验错误引导用户继续输入，
        不应直接抛出系统异常。
    """
```

### Routing

所有条件路由函数必须说明每个分支的含义。

```python
def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """判断 Agent 是否需要继续调用工具。

    Returns:
        "tools": 最新 AIMessage 中存在 tool_calls，需要进入工具节点。
        "end": 无需继续调用工具，本轮图执行结束。
    """
```

## 数据库专项规范

### ORM Model

ORM 模型类必须说明表的业务含义。

字段名不直观、涉及状态机、JSON、软删除、审计、安全的字段必须写注释。

```python
class AgentRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Agent 单次运行记录表。

    一条记录表示一次 graph invoke 或 stream 执行，用于排查问题、
    展示运行历史、关联工具调用和观测 trace。
    """
```

### Repository

Repository 只负责数据访问，不负责业务判断和事务提交。

Repository 方法 docstring 必须说明：

1. 查询条件。
2. 是否包含软删除数据。
3. 是否会修改数据库。
4. 是否主动 commit。

```python
async def get_by_id(self, conversation_id: str) -> Conversation | None:
    """根据 ID 查询未软删除的会话。

    本方法不主动 commit，不控制事务边界。
    """
```

### Service

Service 层负责业务编排和事务边界。

Service 方法 docstring 应说明：

1. 业务目的。
2. 调用了哪些领域对象或 Repository。
3. 事务边界。
4. 关键副作用。

```python
async def delete_conversation(self, conversation_id: str, user_id: str) -> None:
    """软删除指定用户的会话。

    本方法在 Service 层开启事务，负责同时删除会话可见状态并记录审计事件。
    Repository 只执行数据访问，不主动 commit。
    """
```

### 会话 / 恢复编排

如果 Service 同时处理消息持久化、运行记录、checkpoint 恢复，docstring 应补充：

1. 当前方法操作的是“会话视图”还是“LangGraph thread”。
2. 是否需要把结构化输入同步落成普通消息，以保证历史可见。
3. 为什么要选择某个 graph 或 thread 恢复，而不是直接复用默认入口。
4. 哪些元数据只属于中断态，成功后必须清理。

## 外部集成专项规范

以下模块必须写清楚降级策略：

* Redis
* Langfuse
* OpenTelemetry
* LLM Provider
* Object Storage
* Queue
* HTTP Client

示例：

```python
def create_langfuse_client() -> Langfuse | None:
    """创建 Langfuse 客户端。

    当 LANGFUSE_ENABLED=false 或密钥缺失时返回 None。
    可观测性不可用不应阻塞主业务流程。
    """
```

## 安全与审计注释规范

涉及以下内容时，必须写注释说明风险和边界：

* API Key
* JWT
* 权限判断
* 用户输入
* 文件上传
* SQL 查询
* 工具调用
* Agent 自动执行动作
* 审计日志
* 脱敏处理

示例：

```python
# 用户输入只作为工具参数候选，不允许直接拼接 SQL。
```

## 行内注释规范

行内注释只用于解释复杂或不明显的逻辑。

推荐：

```python
# Graph 已在 lifespan 中编译，避免每个请求重复构建导致性能抖动。
graph = request.app.state.graph
```

不推荐：

```python
# 获取 graph
graph = request.app.state.graph
```

## TODO / FIXME 规范

允许使用 TODO，但必须包含责任范围、日期、原因和后续动作。

推荐：

```python
# TODO(backend, 2026-06-07): 接入真实用户系统后替换 anonymous user。
```

```python
# FIXME(backend, 2026-06-07): 当前重试策略未区分限流和网络超时，需要细化异常类型。
```

禁止：

```python
# TODO: optimize
```

## 禁止生成的注释

不要生成这类无意义注释：

```python
# import FastAPI
```

```python
# define class
```

```python
# loop through items
```

```python
# return response
```

```python
# set variable to true
```

这些注释不会提供额外信息，只会增加维护成本。

## AI 编码助手自检清单

修改 Python 代码后，必须检查：

* [ ] 新增 Python 模块是否有模块级 docstring。
* [ ] 新增公开类是否有 class docstring。
* [ ] 新增公开函数是否有 function docstring。
* [ ] Service 层是否说明事务边界。
* [ ] Repository 层是否没有主动 commit。
* [ ] Graph node 是否说明 Reads、Writes、Side Effects。
* [ ] Routing 函数是否说明每个分支含义。
* [ ] 外部集成是否说明失败降级策略。
* [ ] 安全、权限、文件、SQL、工具调用是否说明风险边界。
* [ ] 是否删除了无意义注释。
* [ ] 注释是否与当前代码行为一致。
