# Deployment Notes

本文件用于沉淀部署环境、镜像构建、Compose 编排与上线注意事项。

## 目录约束

- `deploy/` 保持在仓库根目录，服务整个全栈项目。
- `deploy/docker/` 用于后端与前端镜像构建。
- `deploy/compose/` 用于本地联调和环境编排。
- `deploy/nginx/` 用于统一入口与反向代理配置。

## 使用原则

- 后端 Dockerfile 以 `backend/` 为语义上下文。
- 前端 Dockerfile 以 `web/` 为语义上下文。
- Compose 中至少明确 `backend`、`web`、`postgres`、`redis` 的协作关系。
