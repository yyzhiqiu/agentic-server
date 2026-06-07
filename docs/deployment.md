# Deployment

本文件说明 `deploy/` 目录的当前实现、目录边界和本地联调入口。

## 目录定位

`deploy/` 保持在仓库根目录，服务整个全栈项目，而不是只服务后端或前端。

目标结构：

```text
deploy/
├── docker/
│   ├── backend.Dockerfile
│   └── web.Dockerfile
├── compose/
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
└── nginx/
    └── nginx.conf
```

## 当前实现

- `deploy/docker/backend.Dockerfile` 已按 `backend/` 作为构建上下文收口。
- `deploy/docker/web.Dockerfile` 已按 `web/` 作为构建上下文收口，并使用前端目录内的 `pnpm-lock.yaml` 做确定性安装。
- `deploy/compose/docker-compose.yml` 现在包含 `backend`、`web`、`postgres`、`redis`，并补上 `nginx` 作为统一入口。
- `deploy/compose/docker-compose.dev.yml` 提供开发联调版本，保留代码挂载、后端 `uvicorn --reload` 和前端 `pnpm dev`。
- 生产版 `web` 镜像现在内置了 SPA 路由回退，直接刷新 `/chat`、`/conversations/:id` 等地址时仍会回到前端入口页。
- `deploy/nginx/nginx.conf` 现在把 `/v1/`、`/health`、`/ready` 转发到 `backend`，把 `/` 转发到 `web`，并对 `/v1/chat/stream` 关闭代理缓冲以支持流式响应。
- Compose 服务现在补上了基础健康检查和更稳的依赖顺序，便于作为复用模板继续演进。

## 结构契约

当前部署目录遵循以下契约：

- `deploy/docker/backend.Dockerfile` 以 `backend/` 为后端上下文语义。
- `deploy/docker/web.Dockerfile` 以 `web/` 为前端上下文语义。
- `deploy/compose/docker-compose.yml` 与 `deploy/compose/docker-compose.dev.yml` 明确包含：
  - `backend`
  - `web`
  - `postgres`
  - `redis`
- `deploy/nginx/nginx.conf` 明确：
  - `/v1/` 转发到 `backend`
  - `/` 转发到 `web`
  - `/v1/chat/stream` 以非缓冲方式透传流式响应

## Compose 用法

生产风格本地联调：

```bash
cd deploy/compose
docker compose up --build
```

开发风格联调：

```bash
cd deploy/compose
docker compose -f docker-compose.dev.yml up --build
```

当前约定下：

- 生产风格 compose 会暴露：
  - `http://localhost/` 通过 `nginx` 访问前端
  - `http://localhost/v1/...` 通过 `nginx` 反向代理到后端
  - `http://localhost:8000` 可直接访问后端
- 开发风格 compose 会暴露：
  - `http://localhost:5173` 前端 Vite 开发服务
  - `http://localhost:8000` 后端 FastAPI 服务
  - `localhost:5432` PostgreSQL
  - `localhost:6379` Redis

当前 Compose 还包含以下基础健康检查：

- `backend`：检查 `http://127.0.0.1:8000/ready`
- `web`：生产版检查容器内 Nginx 首页，开发版检查 `http://127.0.0.1:5173`
- `postgres`：`pg_isready`
- `redis`：`redis-cli ping`
- `nginx`：检查 `http://127.0.0.1/`

## 环境变量说明

当前 Compose 文件直接内联了后端运行所需的大部分基础环境变量，并为以下项保留外部注入入口：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LANGFUSE_ENABLED`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST`

如果需要改默认值，可优先参考：

- [../backend/.env.example](../backend/.env.example)
- [../web/.env.example](../web/.env.example)

另外，当前 Compose 默认把 `APP_NAME`、`API_PREFIX`、`CACHE_NAMESPACE`、`POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`VITE_APP_NAME`、`VITE_API_BASE_URL` 和 `VITE_API_PREFIX` 都设计成了可覆写入口，便于把这套目录直接复用到新项目中。

根 Nginx 当前默认允许最大 `50 MB` 请求体，以覆盖文件管理页的基础上传场景；如果后续需要更大的文件上传，建议把对象存储方案和反向代理限制一起调整。

## 仍建议补充的内容

当前部署目录已经具备公开仓库可维护的基础骨架，但在真正对外发布或投产前，仍建议补齐以下内容：

- 真实的 `.env` / secret 管理策略
- CI/CD 环境下的镜像发布流程
- 生产数据库、Redis 与对象存储的高可用配置
- HTTPS、域名、证书和更细粒度的 Nginx 缓存策略
- 在真实装有 Docker 的环境里执行 `docker compose config` / `up` 的最终验证

## 相关文档

- [../README.md](../README.md)
- [./architecture.md](./architecture.md)
- [./development.md](./development.md)
