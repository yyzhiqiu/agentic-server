# Web

本文件说明 `web/` 的目录职责、技术栈边界和已提供的基础能力。

## 目录定位

- `web/` 是前端服务根目录。
- 前端采用 `React + TypeScript + Vite`。
- 目录结构按 `pages/`、`features/`、`shared/` 分层组织。
- 现有结构保持目录边界清晰、接口接入路径统一，并为业务扩展保留稳定结构。

## 技术栈约束

- Vite
- React
- TypeScript
- React Router
- TanStack Query
- Tailwind CSS
- shadcn/ui 风格组件
- lucide-react

前端约束：

- 不使用 Next.js。
- 不使用 Ant Design。
- 普通 HTTP 请求可以用 `fetch` 封装。
- 流式聊天使用 `fetch` + `ReadableStream`。

## 目录结构

```text
web/
├── public/
├── src/
│   ├── app/                    # 路由、Provider、QueryClient
│   ├── pages/                  # 页面组件
│   ├── features/               # 业务模块
│   ├── shared/                 # 通用 API、组件、hooks、类型、常量
│   ├── styles/                 # 全局样式
│   └── assets/                 # 打包资源
├── .env.example
├── components.json
├── eslint.config.js
├── package.json
├── postcss.config.js
├── tailwind.config.ts
├── tsconfig.json
└── vite.config.ts
```

## 已提供基础能力

- `web/` 目录和主要子目录已经建立。
- 路由、页面、共享组件和基础 API 封装文件已经就位。
- `Files` 页面已接入文件管理接口，可读取 `/v1/files`，并支持单文件上传、下载、删除能力。
- `Conversations` 列表页和详情页已接入会话数据，可展示历史会话与已持久化消息。
- `Agent Runs` 列表页和详情页已接入运行记录数据，可展示状态摘要、错误信息和工具调用轨迹。
- `Chat` 页面已接入同步聊天与最小可用的流式响应读取能力。

## 启动方式

```bash
cd web
pnpm install
pnpm dev
```

根目录也可以执行：

```bash
pnpm dev:web
pnpm build:web
pnpm lint:web
```

## 协作入口

- [../web/AGENTS.md](../web/AGENTS.md)
- [../AGENTS.md](../AGENTS.md)
- [../docs/architecture.md](../docs/architecture.md)
