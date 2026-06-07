# web/AGENTS.md

本文件用于补充 `web/` 目录下的协作约束，适用于所有 AI 助手和人类协作者。

## 技术栈

- Vite
- React
- TypeScript
- React Router
- TanStack Query
- Tailwind CSS
- shadcn/ui 风格组件
- lucide-react

## 目录边界

- 页面组件放在 `src/pages/`
- 业务模块放在 `src/features/`
- 通用能力放在 `src/shared/`
- shadcn/ui 风格基础组件放在 `src/shared/components/ui/`

## 开发约束

- 不使用 Next.js。
- 不使用 Ant Design。
- 普通 HTTP 请求可以使用 `fetch` 封装。
- 流式聊天使用 `fetch` + `ReadableStream`。
- 当前阶段优先保持结构清晰、可继续演进，不提前堆叠复杂状态管理。
