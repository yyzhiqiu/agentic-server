# Frontend Development

本 skill 面向所有 AI 助手和人类协作者，用于约束 `web/` 开发方式。

## 核心规则

- 使用 React + TypeScript + Vite。
- 页面组件放在 `web/src/pages/`。
- 业务模块放在 `web/src/features/`。
- 通用能力放在 `web/src/shared/`。
- 流式响应使用 `fetch` + `ReadableStream`，不使用 Axios 处理流式聊天。
