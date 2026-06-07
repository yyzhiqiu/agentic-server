# skills

`skills/` 是项目级知识目录，面向所有 AI 助手和人类协作者使用，不属于 `backend/` 或 `web/` 的运行时代码，也不参与构建产物输出。

这里沉淀的是项目共享规则，而不是某个单一 AI 工具的私有提示。不同 AI 助手可以读取这里的规范，人类协作者也可以直接把它当成项目知识库来查阅。

## 目录职责

- 沉淀项目级工程规范
- 统一 AI 协作约束与文档入口
- 为 README、架构文档、代码审查、测试与开发实践提供参考

## 使用原则

- 修改 Python 代码前，优先阅读 [ai/python-commenting.md](./ai/python-commenting.md)。
- 需要完整的 Python Docstring 规范、示例与自检清单时，继续阅读 [python-commenting/SKILL.md](./python-commenting/SKILL.md)。
- 生成项目总览或 README 时，优先参考 `project-overview-generator/`。
- 处理后端、前端、测试、代码审查时，优先参考对应 skill 目录。

## 当前结构

```text
skills/
├── README.md
├── ai/
├── architecture/
├── agent/
├── operations/
├── python-commenting/
├── project-overview-docenerator/
├── project-overview-generator/
├── backend-development/
├── frontend-development/
├── testing/
└── code-review/
```

`project-overview-docenerator/` 目前仅为兼容历史引用保留；新的项目说明和 README 同步优先使用 `project-overview-generator/`。
