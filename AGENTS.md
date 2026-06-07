# AGENTS.md

本文件是所有 AI 编码助手在本仓库工作时必须遵守的项目级规则。

如果某个 AI 工具不自动读取 `AGENTS.md`，请将本文件内容复制或引用到该工具对应的项目规则入口中。

## 项目结构

本项目是浅层 monorepo：

```text
agentic-server/
├── backend/        # FastAPI + LangGraph 后端服务
├── web/            # React + TypeScript + Vite + shadcn/ui 前端服务
├── skills/         # 面向所有 AI 助手和人类协作者的项目级知识库、协作规范与工程经验
├── deploy/         # 部署配置
├── docs/           # 全栈项目文档
└── scripts/        # 项目级脚本
```

约束：

1. 不要创建 `apps/` 目录。
2. `backend/` 是后端服务目录。
3. `web/` 是前端服务目录。
4. `skills/` 是面向所有 AI 助手和人类协作者的项目级知识库，不属于后端或前端运行时代码。
5. `deploy/` 和 `docs/` 保持在根目录，服务整个全栈项目。

## 通用工作规则

1. 修改代码前，先阅读相关目录和已有代码风格。
2. 优先做最小、清晰、可验证的修改。
3. 不要大规模重写已有模块，除非任务明确要求。
4. 不要删除已有业务代码，除非任务明确要求。
5. 不要硬编码 API Key、Token、密码、数据库连接串等敏感信息。
6. 新增配置必须写入对应的 `.env.example`，并从环境变量读取。
7. 修改目录结构时，必须同步更新 README、文档、启动命令和测试路径。
8. 不要引入与当前技术栈冲突的框架或库。

## 后端规则

后端目录：

```text
backend/
├── app/
├── migrations/
├── tests/
├── scripts/
├── alembic.ini
├── requirements.txt
├── pyproject.toml
└── run.py
```

后端约束：

1. 后端内部 Python 包名保持为 `app`。
2. 后端内部 import 使用 `app.xxx`。
3. 不要改成 `backend.app.xxx`。
4. 不要把 `backend/app/` 改名成 `backend/backend/`。
5. 不要在请求期间重复构建 LangGraph graph。
6. Graph、LLM、Redis、HTTP Client、Langfuse 等应用级资源应在 lifespan 或工厂函数中初始化。
7. API 层只处理 HTTP 输入输出，不写复杂业务。
8. Service 层负责业务编排和事务边界。
9. Repository 层只负责数据访问，不主动 commit。
10. Graph 层只负责 Agent 编排，不直接依赖 HTTP 请求对象。

## 前端规则

前端目录：

```text
web/
├── src/
├── public/
├── package.json
├── vite.config.ts
├── components.json
└── tailwind.config.ts
```

前端技术栈：

1. Vite
2. React
3. TypeScript
4. React Router
5. TanStack Query
6. Tailwind CSS
7. shadcn/ui 风格组件
8. lucide-react

前端约束：

1. 不使用 Next.js。
2. 不使用 Ant Design。
3. 不使用 Axios 处理流式响应。
4. 普通 HTTP 请求可以使用 fetch 封装。
5. 流式聊天使用 fetch ReadableStream。
6. shadcn/ui 组件放在 `web/src/shared/components/ui/`。
7. 页面组件放在 `web/src/pages/`。
8. 业务模块放在 `web/src/features/`。
9. 通用能力放在 `web/src/shared/`。

## Python 注释规范

修改或新增 Python 代码时，必须阅读并遵守：

```text
skills/ai/python-commenting.md
```

该文件是项目级 Python 注释入口；更完整的规范与示例位于 `skills/python-commenting/SKILL.md`。

最低要求：

1. 新增 Python 模块必须有模块级 docstring。
2. 新增公开类必须有 class docstring。
3. 新增公开函数必须有 function docstring。
4. Service、Repository、Middleware、Graph Node、Graph Routing、Integration、LLM Factory 必须写清楚职责、边界和副作用。
5. 复杂逻辑必须解释 Why，不要只重复 What。
6. 禁止生成无意义注释，例如 `# return result`、`# initialize variable`。
7. 修改函数行为、返回值、异常、事务边界时，必须同步更新 docstring。

## 后端启动命令

在后端目录执行：

```bash
cd backend
python run.py
```

或：

```bash
cd backend
uvicorn app.main:app --reload
```

数据库迁移在 `backend/` 目录执行：

```bash
cd backend
alembic revision --autogenerate -m "message"
alembic upgrade head
```

## 前端启动命令

在前端目录执行：

```bash
cd web
pnpm install
pnpm dev
```

根目录可以执行：

```bash
pnpm dev:web
pnpm build:web
pnpm lint:web
pnpm dev:backend
pnpm test:backend
pnpm check:env
```

## 完成前自检

每次修改完成前，必须检查：

* [ ] 是否破坏现有目录结构。
* [ ] 是否有不必要的大规模重构。
* [ ] 是否误删已有业务代码。
* [ ] 是否新增了硬编码敏感信息。
* [ ] 新增配置是否写入 `.env.example`。
* [ ] 后端 import 是否仍然使用 `app.xxx`。
* [ ] Python docstring 是否符合 `skills/ai/python-commenting.md`。
* [ ] 后端是否仍可从 `backend/` 启动。
* [ ] 前端是否仍可从 `web/` 启动。
* [ ] README 或 docs 是否需要同步更新。
