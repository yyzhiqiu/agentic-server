# web

`web/` 是本仓库的前端服务目录，采用 `React + TypeScript + Vite` 工程结构，用于提供 Agent 控制台和后端接口的可视化入口。

## 已提供的页面与能力

- `Chat`：同步对话与流式响应
- `Conversations`：历史会话列表与详情读取
- `Agent Runs`：运行记录列表与详情读取
- `Files`：文件列表、上传、下载、删除
- `Settings`：本地配置页入口

## 技术栈

- Vite
- React
- TypeScript
- React Router
- TanStack Query
- Tailwind CSS
- shadcn/ui 风格组件
- lucide-react

## 目录约定

- `src/app/`：应用级路由与 Provider
- `src/pages/`：页面组件
- `src/features/`：业务模块
- `src/shared/`：通用 API、组件、hooks、类型与常量
- `src/styles/`：全局样式

## 环境变量

参考 [./.env.example](./.env.example)：

```bash
VITE_APP_NAME=Agent Platform
VITE_API_BASE_URL=http://localhost:8000
VITE_API_PREFIX=/v1
```

## 启动方式

```bash
cd web
pnpm install
pnpm dev
```

也可以在仓库根目录执行：

```bash
pnpm dev:web
pnpm build:web
pnpm lint:web
```

## 协作入口

- [../AGENTS.md](../AGENTS.md)
- [./AGENTS.md](./AGENTS.md)
- [../docs/web.md](../docs/web.md)
