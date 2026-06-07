# Backend Development

本 skill 面向所有 AI 助手和人类协作者，用于约束 `backend/` 开发方式。

## 核心规则

- API 层只处理 HTTP 输入输出。
- Service 层负责业务编排和事务边界。
- Repository 层只负责数据访问，不主动 `commit`。
- Graph、LLM、Redis、HTTP Client、Langfuse 等资源在应用初始化阶段创建。
