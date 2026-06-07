---
name: project-overview-generator
description: Use when the repository needs a project overview or README aligned with the repository's real structure, configs, and docs. The output should be evidence-first and avoid inventing unsupported facts.
---

# Project Overview Generator

本 skill 用于生成或更新项目概览类文档，默认读者包含所有 AI 助手和人类协作者。

## 目标

- 基于仓库真实结构生成 README 或项目总览文档
- 保持证据优先，不虚构部署地址、账号、环境入口
- 强调目录职责、启动方式与协作边界

## 当前仓库约定

- 生成根 README 时，优先基于 `AGENTS.md`、`项目目录结构.txt`、现有目录结构与配置文件。
- `skills/` 应描述为项目级知识目录，而非单一 AI 工具专用目录。
- 如果旧目录 `project-overview-docenerator/` 仍存在，优先参考其已有说明并逐步迁移。
