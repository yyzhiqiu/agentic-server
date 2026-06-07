# backend/AGENTS.md

本文件用于补充 `backend/` 目录下的协作约束，适用于所有 AI 助手和人类协作者。

## 目录边界

- `backend/` 是后端服务执行根目录。
- Python 包名固定为 `app`。
- 后端内部 import 统一使用 `app.xxx`，不要改成 `backend.app.xxx`。

## 开发约束

- API 层只处理 HTTP 输入输出、依赖注入和异常映射。
- Service 层负责业务编排与事务边界。
- Repository 层只负责数据访问，不主动 `commit`。
- Graph、LLM、Redis、HTTP Client、Langfuse 等应用级资源应在 lifespan 或工厂函数中初始化。
- 不要在请求期间重复构建 LangGraph graph。

## 注释与文档

- 修改或新增 Python 代码前，请先阅读 [../skills/ai/python-commenting.md](../skills/ai/python-commenting.md)。
- 新增公开模块、公开类、公开函数时，必须补齐 docstring。

## 启动与测试

常用命令：

```bash
cd backend
python run.py
python -m pytest
alembic upgrade head
```
