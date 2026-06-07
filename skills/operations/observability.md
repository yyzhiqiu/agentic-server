# Observability Notes

本文件用于沉淀日志、trace、metrics、Langfuse 等可观测性约束。

## 基本原则

- 请求链路应尽量保留 `trace_id` 与 `request_id`，便于跨层排查。
- 日志、审计、运行记录与工具调用记录应形成互补关系，而不是互相替代。
- 可选的 Langfuse、metrics 与 tracing 集成应支持显式启用和降级关闭。

## 工程建议

- API 响应、后台任务与工具调用都应尽量保留最小可追踪上下文。
- 指标与告警策略应优先围绕错误率、耗时、依赖可用性和关键业务链路设计。
