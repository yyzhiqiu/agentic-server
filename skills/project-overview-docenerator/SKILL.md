---
name: project-overview-doc-generator
description: Use when a repository needs a company-standard project overview document based on real code, config, and docs, especially when fixed top-level sections are required and unsupported facts must stay explicitly pending instead of being invented.
---

# Project Overview Doc Generator

## Overview

为任意代码仓库生成统一规格的“项目说明文档”。核心原则只有两个：

1. 一级章节保持公司模板风格稳定
2. 所有内容必须由当前仓库中的真实证据支撑；没有证据就明确留空或标注待补充

## When to Use

- 用户要你“补全项目说明文档”“生成项目概述文档”“按统一模板写项目介绍”
- 用户强调要基于真实代码、真实配置、真实目录，而不是泛化模板
- 输出需要适配不同项目，但又必须保留固定的公司章节结构
- 目标产物是“项目总览 / 项目说明”，不是系统设计、接口设计或部署手册

## Do Not Use

- 用户只是要改普通 README 营销文案
- 用户允许自由写技术方案，不要求固定模板
- 目标仓库几乎没有代码和配置，无法提供最基本的证据
- 用户要写系统设计说明书、详细部署手册、接口文档或安全设计
- 仓库已经有成熟 README，只是做一次小范围同步更新；这类场景优先走 `skills/doc-sync/SKILL.md`
- 用户要的是架构方案推演，而不是基于当前仓库事实生成项目总览

## Output Rules

- 默认输出文件：`PROJECT_OVERVIEW.md`
- 默认**不要**覆盖根目录 `README.md`
- 只有用户明确要求时，才允许把结果写回 `README.md`
- 如果仓库根 `README.md` 已经承担“项目说明 / 项目总览”职责，且用户要求更新该入口，则切到 `skills/doc-sync/SKILL.md`，把 README 作为落点，不再并行生成第二份总览
- 如果新生成 `PROJECT_OVERVIEW.md` 且仓库存在 `docs/目录索引.md` 或等价索引，需同步补入口，避免文档不可发现；这一步同样按 `skills/doc-sync/SKILL.md` 的路由执行
- 一级标题保持以下结构：
  - `1. 项目概述`
  - `2. 技术架构`
  - `3. 核心组件与目录结构`
  - `4. 本地开发环境`
  - `5. 项目部署与环境访问`
- 二级内容允许按项目真实结构展开，不要把所有项目硬写成同一种“前后端 + 数据库”模板
- 输出是“项目总览文档”，不是需求文档、详细设计文档或运维手册；缺失细节要引用现有文档入口，不要在这里扩写成另一套正式设计

## Evidence-First Workflow

### 1. 先加载模板

- 优先读取技能内模板：`templates/project-overview-template.md`
- 如果仓库根目录 `README.md` 明确就是公司模板，可以把它当作表现形式参考
- 不要把根目录 `README.md` 当作唯一依赖；技能必须可独立迁移到别的仓库
- 模板只提供章节骨架和证据落位方式，不是“把占位符逐项补满”的问卷

### 2. 再读高信号证据

优先顺序如下：

1. 根目录说明文档与架构文档：`README*`、`ARCHITECTURE*`、`AGENTS.md`、`CLAUDE.md`
2. 包管理与运行时清单：`pyproject.toml`、`package.json`、`go.mod`、`pom.xml`、`build.gradle*`
3. 本地启动与部署文件：`docker-compose*.yml`、`Dockerfile*`、`Makefile`、`Taskfile.yml`
4. 目录结构：顶层源码目录、`tests/`、`deploy/`、`scripts/`
5. 前端 / 后端子项目清单：如 `ui/*/package.json`、`server/*/pyproject.toml`
6. 部署与环境资料：`deploy/`、`docker/`、`charts/`、`kubernetes/`

### 3. 忽略低价值噪音目录

默认忽略：

- `.git/`
- `.venv/`
- `node_modules/`
- `.next/`
- `out/`
- `dist/`
- `coverage/`
- `__pycache__/`
- IDE 缓存目录（如 `.idea/`）

### 4. 按章节映射证据

#### 项目概述

- 从架构文档、包描述、仓库首页文档抽取“项目是什么”
- 说明核心职责、主要组成、服务对象
- 不要照抄营销口号；要落到真实能力边界

#### 技术架构

- 按项目实际形态拆分
- 可以是“前端 / 后端 / 数据 / 运维”
- 也可以是“SDK / Gateway / Dashboard / Deployment”
- 如果项目不是传统三层架构，不要强行套壳

#### 核心组件与目录结构

- 只列核心目录，不要把整个根目录机械展开
- 每个目录后面都要写职责
- 职责说明要来自真实代码布局或文档，而不是凭名字猜

#### 本地开发环境

- 优先写真实可执行的启动路径
- 如果仓库同时支持源码启动和容器启动，优先都写出来
- 启动命令必须直接来自仓库文件或仓库文档
- 不要暴露本地私密值；环境变量只写变量名或示例值
- 若仓库没有公开克隆地址或固定管理员账号，不要按常见模板补一个“看起来完整”的版本

#### 项目部署与环境访问

- 部署指南优先引用仓库内可见文档或部署目录
- 对“测试/预发/生产地址”“公司 Wiki 链接”“固定管理员账号”之类信息：
  - 有证据才写
  - 没有证据就写“当前仓库未发现直接证据，请运维补充”

## Strict Evidence Mode

必须遵守以下约束：

- 不编造 Git 仓库地址、部署链接、环境地址、账号密码
- 不把“常见做法”写成“当前项目事实”
- 不把代码中出现过的示例值当成正式生产配置
- 如果证据不足，使用以下表达之一：
  - `当前仓库未发现直接证据`
  - `请由运维补充`
  - `当前仓库仅提供开发示例`
- 对外链、公司 Wiki、测试/预发/生产地址、默认账号密码，宁可留缺口，也不要用模板示例或内网示例“代填”

## Recommended Output Strategy

生成前先做一次落点判定：

1. **已有 README 承担项目说明职责**
   - 用户要更新仓库主入口时：直接更新 `README.md`
   - 不要同时再生成一份 `PROJECT_OVERVIEW.md`

2. **仓库缺少统一项目总览**
   - 生成 `PROJECT_OVERVIEW.md`
   - 如仓库存在文档索引，再补索引入口

3. **用户只要小范围文案同步**
   - 不启用本技能
   - 切换到 `skills/doc-sync/SKILL.md`

4. **用户要系统设计 / 部署细节 / 接口契约**
   - 不把总览文档扩写成详细设计
   - 分别切到对应的设计或契约技能

## Recommended Validation

生成后至少做这 6 项检查：

1. `PROJECT_OVERVIEW.md` 已生成，且未误覆盖 `README.md`
2. 文档中不存在模板残留占位符或提示语，如 `[在此填写...]`、`请填写`、`例如：`
3. 技术栈、端口、启动命令能在源文件中找到对应证据
4. 没有证据的环境链接、账号密码被明确标成待补充，而不是被伪造
5. 文档中不存在模板演示残留，如 `点击此处跳转`、`模版示例`、`开发岗负责完善`、`运维岗负责完善`
6. 如本次新增 `PROJECT_OVERVIEW.md`，已确认是否需要同步 README 入口或 `docs/目录索引.md`

## Common Mistakes

- 把所有项目都写成“前端 + 后端 + MySQL + Redis”的通用壳子
- 从本机 `.env` 直接抄敏感值进说明文档
- 只看一个 `README` 就下结论，不核对真实包清单和部署文件
- 明明没有环境访问文档，还硬写测试/生产地址
- 明明网关 + SDK + UI 是分层结构，却压扁成一句“AI 平台”
- 明明 README 已是仓库主入口，却又平行再造一份无人维护的 `PROJECT_OVERVIEW.md`
- 把模板里的演示链接、默认账号或“开发岗负责完善”原样带进最终文档

## Example

- 示例输出见：`examples/litellm-project-overview.md`