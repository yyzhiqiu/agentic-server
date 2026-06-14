# shadcn/ui Skill

## 目标

本 Skill 用于指导大模型在当前项目中正确使用 shadcn/ui 构建前端界面。

当前项目默认技术栈：

- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Radix UI primitives
- lucide-react icons
- 可选：react-hook-form、zod、TanStack Table、TanStack Query

当用户要求创建、修改、重构或优化前端 UI 时，应优先遵循本文件。

---

## 适用场景

当任务涉及以下内容时，必须使用本 Skill：

- 页面 UI
- 表单
- 弹窗
- 抽屉
- 卡片
- 导航栏
- 侧边栏
- 数据表格
- 登录页
- 注册页
- 设置页
- Dashboard
- Admin 页面
- Chat UI
- 空状态
- Loading 状态
- Error 状态
- 主题切换
- 深色模式
- 响应式布局
- 组件重构
- Tailwind 样式调整

---

## 核心原则

1. 优先使用 shadcn/ui 组件，不要重复手写基础组件。
2. 不要臆造不存在的组件、props、导入路径或 API。
3. 使用前必须检查项目中是否已有对应组件。
4. 缺少组件时，应使用 shadcn CLI 添加，而不是手动凭记忆创建。
5. shadcn/ui 组件是复制到项目中的代码，可以定制，但必须保持组件语义和可维护性。
6. 不要混用多个大型 UI 框架。
7. 不要引入 Ant Design、Material UI、Chakra UI、Mantine，除非用户明确要求。
8. 不要为了一个简单 UI 引入过重依赖。
9. 代码必须类型安全、结构清晰、可维护。
10. 组件必须兼容深色模式，不能只写浅色模式。

---

## 工作前检查

在实现 UI 之前，先检查项目结构。

优先查找以下文件：

```txt
components.json
tailwind.config.ts
tailwind.config.js
postcss.config.js
src/index.css
src/app/globals.css
app/globals.css
components/ui
src/components/ui
lib/utils.ts
src/lib/utils.ts
```

如果存在 `components.json`，优先读取其中的 aliases 配置，不要假设一定使用 `@/components/ui`。

常见 alias：

```json
{
  "aliases": {
    "components": "@/components",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "utils": "@/lib/utils",
    "hooks": "@/hooks"
  }
}
```

如果项目使用 `src` 目录，常见结构为：

```txt
src/
  components/
    ui/
    common/
    layout/
  features/
  hooks/
  lib/
  app/
```

如果项目不使用 `src` 目录，常见结构为：

```txt
components/
  ui/
  common/
  layout/
features/
hooks/
lib/
app/
```

实现时必须尊重项目已有结构。

---

## 初始化规则

如果项目尚未初始化 shadcn/ui，先不要直接写组件代码，应建议或执行初始化命令。

npm：

```bash
npx shadcn@latest init
```

pnpm：

```bash
pnpm dlx shadcn@latest init
```

yarn：

```bash
yarn shadcn@latest init
```

bun：

```bash
bunx shadcn@latest init
```

初始化后应确认：

- 已生成或更新 `components.json`
- 已配置 Tailwind CSS
- 已生成 `cn` 工具函数
- 已配置 CSS variables
- 已生成 `components/ui` 目录

---

## 添加组件规则

缺少组件时，优先使用 shadcn CLI 添加。

npm：

```bash
npx shadcn@latest add button
```

pnpm：

```bash
pnpm dlx shadcn@latest add button
```

常用组件安装命令：

```bash
npx shadcn@latest add button
npx shadcn@latest add input
npx shadcn@latest add label
npx shadcn@latest add textarea
npx shadcn@latest add checkbox
npx shadcn@latest add radio-group
npx shadcn@latest add select
npx shadcn@latest add switch
npx shadcn@latest add slider
npx shadcn@latest add form
npx shadcn@latest add card
npx shadcn@latest add dialog
npx shadcn@latest add alert-dialog
npx shadcn@latest add sheet
npx shadcn@latest add drawer
npx shadcn@latest add popover
npx shadcn@latest add dropdown-menu
npx shadcn@latest add command
npx shadcn@latest add tabs
npx shadcn@latest add table
npx shadcn@latest add badge
npx shadcn@latest add avatar
npx shadcn@latest add separator
npx shadcn@latest add skeleton
npx shadcn@latest add alert
npx shadcn@latest add toast
npx shadcn@latest add sonner
npx shadcn@latest add tooltip
npx shadcn@latest add breadcrumb
npx shadcn@latest add pagination
npx shadcn@latest add navigation-menu
npx shadcn@latest add sidebar
npx shadcn@latest add calendar
npx shadcn@latest add date-picker
```

不要一次性安装无关组件。根据页面需求只添加必要组件。

---

## 导入规则

优先使用项目 alias。

常见写法：

```tsx
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
```

如果 `components.json` 中配置了不同 alias，必须按项目实际配置导入。

禁止写法：

```tsx
import { Button } from "shadcn/ui"
import Button from "@/components/ui/Button"
import { Button } from "@/ui/button"
```

除非项目中确实存在这些路径。

---

## 目录约定

基础 UI 组件：

```txt
components/ui
```

或：

```txt
src/components/ui
```

这些组件一般由 shadcn CLI 管理。

通用业务组件：

```txt
components/common
src/components/common
```

布局组件：

```txt
components/layout
src/components/layout
```

功能模块组件：

```txt
features/<feature-name>/components
src/features/<feature-name>/components
```

页面级组件：

```txt
app/<route>/page.tsx
src/pages
src/routes
```

不要把所有组件都塞进 `components/ui`。

`components/ui` 只放基础 UI primitive。

---

## 组件选择指南

### 按钮

使用 `Button`。

适用场景：

- 提交
- 保存
- 删除
- 取消
- 打开弹窗
- 触发操作

常用 variant：

```tsx
<Button>Save</Button>
<Button variant="secondary">Cancel</Button>
<Button variant="outline">Back</Button>
<Button variant="ghost">More</Button>
<Button variant="destructive">Delete</Button>
<Button size="sm">Edit</Button>
<Button size="icon">...</Button>
```

规则：

- 删除、危险操作使用 `variant="destructive"`。
- 次要操作使用 `secondary`、`outline` 或 `ghost`。
- 图标按钮必须提供可访问名称，例如 `aria-label`。

---

### 输入框

使用：

- `Input`
- `Textarea`
- `Label`
- `Form`
- `Select`
- `Checkbox`
- `RadioGroup`
- `Switch`