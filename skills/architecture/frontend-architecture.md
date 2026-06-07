# Frontend Architecture

本文件用于沉淀 `web/` 的页面分层、业务模块、共享能力与组件约束。

## 目录边界

- 页面组件放在 `web/src/pages/`，按路由组织页面入口。
- 业务模块放在 `web/src/features/`，封装 API、hooks、types 与领域工具。
- 通用能力放在 `web/src/shared/`，集中放置基础组件、通用 API 封装、类型、常量与工具函数。

## 技术约束

- 使用 `Vite + React + TypeScript + React Router + TanStack Query`。
- 普通 HTTP 请求使用 `fetch` 封装。
- 流式聊天使用 `fetch + ReadableStream`，不使用 Axios 处理流式响应。
- shadcn/ui 风格基础组件放在 `web/src/shared/components/ui/`。

## 演进原则

- 优先保持 `pages/`、`features/`、`shared/` 边界清晰，再扩展业务能力。
- 页面文案、导航和环境配置尽量保持通用，不把单一项目的阶段性描述写死在运行时界面。
