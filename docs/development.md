# Development

本文件说明仓库的开发入口、常用命令和协作约定。

目录结构的权威说明见 [../项目目录结构.txt](../项目目录结构.txt)。如果后续修改目录结构，必须同步更新 README、文档、启动命令和测试路径。

## 根目录常用命令

在仓库根目录可执行：

```bash
pnpm dev:web
pnpm build:web
pnpm lint:web
pnpm dev:backend
pnpm test:backend
pnpm check:env
pnpm compose:up
pnpm compose:dev
```

这些命令由根目录 [../package.json](../package.json) 统一提供，方便直接操作子项目。

## 后端开发

在 `backend/` 目录执行：

```bash
cd backend
python run.py
```

或：

```bash
cd backend
uvicorn app.main:app --reload
```

后端测试：

```bash
cd backend
python -m pytest
```

数据库迁移：

```bash
cd backend
alembic revision --autogenerate -m "message"
alembic upgrade head
```

环境变量入口：

- [../backend/.env.example](../backend/.env.example)

## 前端开发

在 `web/` 目录执行：

```bash
cd web
pnpm install
pnpm dev
```

构建与检查：

```bash
cd web
pnpm build
pnpm lint
```

环境变量入口：

- [../web/.env.example](../web/.env.example)

## 部署联调

当前仓库已经补齐基础部署配置，可在 `deploy/compose/` 下使用 Docker Compose 做整套联调。

生产风格本地联调：

```bash
cd deploy/compose
docker compose up --build
```

也可以在仓库根目录执行：

```bash
pnpm compose:up
```

开发风格联调：

```bash
cd deploy/compose
docker compose -f docker-compose.dev.yml up --build
```

也可以在仓库根目录执行：

```bash
pnpm compose:dev
```

目录入口：

- [../deploy/docker/](../deploy/docker/)
- [../deploy/compose/](../deploy/compose/)
- [../deploy/nginx/](../deploy/nginx/)
- [./deployment.md](./deployment.md)

## 项目级规则入口

开始修改前，优先阅读：

- [../AGENTS.md](../AGENTS.md)
- [../backend/AGENTS.md](../backend/AGENTS.md)
- [../web/AGENTS.md](../web/AGENTS.md)
- [../skills/README.md](../skills/README.md)

如果要修改 Python 代码，还需要先阅读：

- [../skills/ai/python-commenting.md](../skills/ai/python-commenting.md)

## 开发约定

- 优先做最小、清晰、可验证的修改
- 修改结构或命令时同步更新 README 与 `docs/`
- 后端内部 import 统一使用 `app.xxx`
- 前端目录边界遵循 `pages/`、`features/`、`shared/`
- 变更 Python 代码前优先阅读 [../skills/ai/python-commenting.md](../skills/ai/python-commenting.md)
