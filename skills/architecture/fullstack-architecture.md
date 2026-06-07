# Fullstack Architecture

本文件用于描述 `backend/`、`web/`、`deploy/`、`docs/` 与 `skills/` 之间的关系。

## 总体原则

- 仓库采用浅层 monorepo。
- 顶层直接使用 `backend/`、`web/`、`skills/`、`deploy/`、`docs/`、`scripts/`。
- 不创建 `apps/` 目录。
- 当前结构基线以根目录 `项目目录结构.txt` 为准。

## 目录关系

- `backend/`：后端服务目录，负责 FastAPI、LangGraph、数据库、对象存储与后端测试。
- `web/`：前端服务目录，负责控制台 UI、页面路由、业务模块与接口接入。
- `deploy/`：全栈部署目录，负责镜像、Compose 和反向代理配置。
- `docs/`：全局项目文档目录，负责记录结构、开发、部署和专题说明。
- `skills/`：项目级知识目录，面向所有 AI 助手和人类协作者，用于沉淀架构知识、协作规范、工程经验和文档生成规则。
- `scripts/`：项目级脚本目录，服务整个 monorepo，不替代 `backend/scripts/`。

## 关键边界

- `skills/` 不属于运行时代码，不参与 `backend/` 或 `web/` 构建。
- 后端内部 import 统一使用 `app.xxx`，不使用 `backend.app.xxx`。
- 前端目录按 `pages/`、`features/`、`shared/` 分层。
- `deploy/` 与 `docs/` 保持在根目录，不下沉到单个服务。

## 当前推进方式

当前按以下顺序推进：

1. 项目结构
2. 后端
3. 前端
4. 部署

这样做的目标是先稳定目录边界和协作入口，再逐步补真实能力，避免一次性扩展过多导致质量下降。
