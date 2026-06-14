# Python 注释与 Docstring 规范

本文件是项目级 Python 注释入口，适用于 `backend/` 下的 Python 代码，也适用于仓库内新增的其他 Python 脚本。

完整说明与更多示例见 [../python-commenting/SKILL.md](../python-commenting/SKILL.md)。

## 先看这 5 条

- 先写清晰代码，再用注释补上下文。
- 注释优先解释 Why、边界、副作用、降级策略，不重复代码表面含义。
- 新增 Python 模块、公开类、公开函数必须有 docstring。
- 修改函数行为、状态流转、异常语义、事务边界时，必须同步更新原有 docstring。
- 所有新增或修改的注释统一使用中文。

## 最低要求

- 新增 Python 模块必须有模块级 docstring。
- 新增公开类必须有 class docstring。
- 新增公开函数必须有 function docstring。
- Service、Repository、Middleware、Graph Node、Graph Routing、Integration、LLM Factory 需要明确职责、边界和副作用。
- 复杂逻辑优先解释 Why，不重复 What。

## 修改现有代码时的最小动作

- 改了公开函数的输入、输出、异常、返回结构，就同步改 docstring。
- 改了 Graph 节点读写的 state 字段，就补清楚 Reads、Writes、Side Effects。
- 改了 Service 编排流程，就写清楚事务边界、持久化时机、调用顺序。
- 改了外部集成逻辑，就补清楚失败时是报错、重试还是降级。

## AI 助手优先补注释的场景

- LangGraph 的节点、路由、interrupt/resume、checkpoint 恢复逻辑。
- Service 层的事务边界、幂等处理、消息持久化与状态迁移。
- Repository 中带筛选条件、软删除语义、批量更新、副作用的查询。
- 调用 LLM、MCP、HTTP、Redis、对象存储等外部系统的适配层。
- 安全相关逻辑，如鉴权、权限判断、用户输入处理、文件与 SQL 边界。

## 禁止写的注释

- `# 获取 graph`
- `# 遍历列表`
- `# 返回结果`
- `# 设置变量`

这类注释没有提供额外信息，只会增加噪音。

## 推荐补法

- 对复杂函数先补 docstring，再用 1 到 3 条行内注释解释关键分支。
- 对 Graph 节点写清楚“读取什么状态、写回什么状态、何时重试、失败后走哪条分支”。
- 对恢复执行逻辑写清楚“为什么要这样拼接 metadata / thread / checkpoint”。

## 自检清单

- docstring 是否和当前行为一致
- 是否说明了事务边界或降级策略
- 是否删除了无意义注释
- 是否补充了安全、权限、文件、SQL、工具调用相关边界说明
