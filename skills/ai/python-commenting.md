# Python 注释与 Docstring 规范

本文件是项目级 Python 注释入口，适用于 `backend/` 下的 Python 代码，也适用于仓库内新增的其他 Python 脚本。

## 最低要求

- 新增 Python 模块必须有模块级 docstring。
- 新增公开类必须有 class docstring。
- 新增公开函数必须有 function docstring。
- Service、Repository、Middleware、Graph Node、Graph Routing、Integration、LLM Factory 需要明确职责、边界和副作用。
- 复杂逻辑优先解释 Why，不重复 What。

## 使用方式

- 在 AI 助手工作流中，将本文件作为 Python 注释规范入口。
- 如需完整说明与示例，可继续阅读 [../python-commenting/SKILL.md](../python-commenting/SKILL.md)。

## 自检清单

- docstring 是否和当前行为一致
- 是否说明了事务边界或降级策略
- 是否删除了无意义注释
- 是否补充了安全、权限、文件、SQL、工具调用相关边界说明
