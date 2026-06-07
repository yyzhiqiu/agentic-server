# Architecture

本文件描述当前仓库的结构基线、目录边界和工程原则。当前权威结构说明以 [../项目目录结构.txt](../项目目录结构.txt) 为准。

## 总体结构

仓库采用浅层 monorepo，直接使用以下顶层目录，不使用 `apps/`：

```text
project-root/
├── backend/    # FastAPI + LangGraph 后端服务
├── web/        # React + TypeScript + Vite 前端服务
├── skills/     # 面向所有 AI 助手和人类协作者的项目级知识目录
├── deploy/     # 全栈部署配置
├── docs/       # 全栈项目文档
└── scripts/    # 项目级脚本
```

结构原则：

- 顶层目录只承载源码、配置、文档和项目脚本。
- 运行时缓存、测试缓存、本地对象存储和临时目录不计入目标结构。
- README、文档、启动命令和测试路径需要与目录结构同步维护。

## 后端边界

- `backend/` 是后端服务执行根目录。
- 后端内部 Python 包名固定为 `app`。
- 后端内部 import 统一使用 `app.xxx`，不要改成 `backend.app.xxx`。
- `backend/` 下保留 `app/`、`migrations/`、`tests/`、`scripts/`、`run.py`、`alembic.ini` 等后端专属内容。
- `backend/app/graph/` 当前采用 `Agent Registry + 多个独立 Agent graph` 结构，对外暴露 `chat_agent`、`code_agent` 等能力，而不是 supervisor / handoff 协作模式。
- Graph、LLM、Redis、HTTP Client、Langfuse 等应用级资源在启动阶段初始化，不在请求期间重复构建。

详细约束见：

- [../backend/AGENTS.md](../backend/AGENTS.md)
- [./backend.md](./backend.md)

## 前端边界

- `web/` 是前端服务执行根目录。
- 前端采用 `Vite + React + TypeScript + React Router + TanStack Query + Tailwind CSS + shadcn/ui`。
- 页面组件放在 `web/src/pages/`。
- 业务模块放在 `web/src/features/`。
- 通用能力放在 `web/src/shared/`。
- 不使用 Next.js，不使用 Ant Design。

详细说明见：

- [../web/AGENTS.md](../web/AGENTS.md)
- [./web.md](./web.md)

## skills 边界

- `skills/` 是项目级知识目录，不属于 `backend/` 或 `web/` 的运行时代码。
- `skills/` 面向所有 AI 助手和人类协作者，用于沉淀架构说明、协作规则、工程经验和文档生成规范。
- 后端和前端代码中都不应直接 import `skills/`。
- 生成 README 或项目说明文档时，优先参考 `skills/project-overview-generator/`。

入口说明见：

- [../skills/README.md](../skills/README.md)

## 部署与运维入口

- `deploy/` 保留在根目录，服务整个全栈项目。
- `docs/` 用于记录架构、开发、部署与运行说明。
- `scripts/` 用于根目录级辅助脚本，不替代 `backend/scripts/` 中的后端专属脚本。

## 结构原则

- 优先保持服务边界清晰，再逐步扩展业务能力
- 避免把仅适用于单一项目的约定硬编码进模板骨架
- 对外文档、环境变量和部署入口应尽量保持通用、可复用、可公开维护
