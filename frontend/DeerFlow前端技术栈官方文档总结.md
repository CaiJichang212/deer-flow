# DeerFlow前端技术栈官方文档总结

本文档汇总了 DeerFlow 前端项目使用的主要技术栈的官方文档资料，为大家研究学习提供参考。

## 1. Next.js 16 with App Router

### 核心特性

- **App Router**：基于文件系统的路由系统，使用 React 最新特性如 Server Components、Suspense 等
- **TurboPack**：默认启用，提供更快的构建速度
- **Server Components**：支持服务器端组件，减少客户端包大小
- **数据获取**：内置 fetch API 扩展，支持自动缓存和重验证
- **路由处理**：支持动态路由、嵌套路由、并行路由等

### 官方文档

- [Next.js 官方文档](https://nextjs.org/docs/app)
- [App Router 入门指南](https://nextjs.org/docs/app/getting-started)
- [Next.js 16 升级指南](https://github.com/vercel/next.js/blob/a41bef94c5ec99cf71e286b8be02dca850b80062/docs/01-app/02-guides/upgrading/version-16.mdx)

### 系统要求

- Node.js 20.9+
- 浏览器支持：Chrome 111+、Edge 111+、Firefox 111+、Safari 16.4+

## 2. React 19

### 核心特性

- **Actions**：处理异步操作的新机制，简化表单处理
- **useActionState**：管理表单提交状态和错误
- **useOptimistic**：实现乐观更新，提升用户体验
- **use**：在渲染过程中加载 Promise 或上下文值
- **Server Components**：正式稳定版，仅在服务器运行
- **Server Actions**：使用 "use server" 标记在客户端代码中运行服务器端函数
- **Ref 作为 Prop**：直接将 refs 传递给函数组件，减少 forwardRef 的使用
- **Context 作为 Provider**：直接使用上下文对象作为 provider 元素

### 官方文档

- [React 官方文档](https://react.dev)
- [React 19 发布公告](https://zh-hans.react.dev/blog/2024/12/05/react-19)
- [React 19 升级指南](https://react.dev/blog/2024/12/05/react-19#upgrading)

## 3. Tailwind CSS 4

### 核心特性

- **新的高性能引擎**：全构建速度提升 3.5 倍，增量构建速度提升 8 倍
- **CSS 优先配置**：直接在 CSS 中自定义和扩展框架
- **CSS 主题变量**：所有设计令牌作为原生 CSS 变量暴露
- **简化安装**：更少的依赖，零配置，只需一行 CSS 代码
- **内置导入支持**：无需额外工具即可捆绑多个 CSS 文件
- **现代 Web 特性**：利用级联层、注册的自定义属性、color-mix() 等
- **容器查询**：基于容器大小的样式，无需插件

### 官方文档

- [Tailwind CSS 官方文档](https://tailwindcss.com/docs)
- [Tailwind CSS v4 发布公告](https://tailwindcss.com/blog/tailwindcss-v4)
- [Tailwind CSS v4.1 发布公告](https://tailwindcss.com/blog/tailwindcss-v4-1)
- [从 v3 升级到 v4 指南](https://tailwindcss.com/docs/upgrade-guide)

### 浏览器支持

- Chrome 111+（2023年3月发布）
- Safari 16.4+（2023年3月发布）
- Firefox 128+（2024年7月发布）

## 4. Shadcn UI

### 核心特性

- **可定制组件**：漂亮设计的组件，可自定义、扩展和构建
- **代码分发平台**：与你喜欢的框架配合使用
- **Monorepo 支持**：在 monorepo 结构中轻松使用
- **组件注册表**：创建和分享自己的组件注册表
- **TypeScript 支持**：完整的类型定义
- **Tailwind CSS 集成**：与 Tailwind CSS 无缝集成

### 官方文档

- [Shadcn UI 官方文档](https://ui.shadcn.com/docs)
- [Shadcn UI GitHub 仓库](https://github.com/shadcn-ui/ui)
- [Monorepo 使用指南](https://www.shadcn.com.cn/docs/monorepo)
- [组件注册表指南](https://www.shadcn-ui.cn/docs/registry/getting-started)

## 5. MagicUI

### 核心特性

- **为设计工程师设计**：专注于设计工程师的工作流程
- **动画组件**：丰富的动画组件和效果
- **可复制粘贴**：组件可以直接复制粘贴到应用中
- **开源免费**：完全开源，免费使用
- **高度可定制**：通过 props 提供丰富的定制选项
- **现代技术栈**：基于现代前端技术构建

### 官方文档

- [MagicUI 官方文档](https://magicui.design/docs)
- [MagicUI GitHub 仓库](https://github.com/magicuidesign/magicui)
- [MagicUI 旧版本文档](https://magicui.design/docs/legacy)

## 6. React Bits

### 核心特性

- **丰富的动画组件**：110+ 动画组件，包括文本动画、UI 元素和背景
- **轻量级**：最小化依赖，支持树摇
- **高度可定制**：通过 props 调整一切，或直接编辑源代码
- **多技术栈支持**：每个组件提供 4 种变体（JS-CSS、JS-TW、TS-CSS、TS-TW）
- **即插即用**：适用于任何现代 React 项目
- **创意工具**：提供背景工作室、形状魔术、纹理实验室等工具

### 官方文档

- [React Bits 官方文档](https://reactbits.dev)
- [React Bits GitHub 仓库](https://github.com/DavidHDev/react-bits)

## 7. LangGraph SDK

### 核心特性

- **异步/同步支持**：同时提供异步和同步客户端
- **类型安全**：完整的 Pydantic 模型定义
- **自动重试**：内置 HTTP 请求重试机制
- **流式处理**：支持 Server-Sent Events (SSE)
- **环境感知**：自动检测 API 密钥和服务器地址
- **认证与授权**：灵活的认证和授权系统
- **持久执行**：构建能够在故障后恢复的代理
- **人工干预**：在执行过程中无缝整合人工监督

### 官方文档

- [LangGraph 官方文档](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph JavaScript 文档](https://docs.langchain.com/oss/javascript/langgraph/overview)
- [LangGraph SDK NPM 包](https://www.npmjs.com/package/@langgraph-js/sdk)
- [LangGraph GitHub 仓库](https://github.com/langchain-ai/langgraph)

## 8. Vercel AI Elements

### 核心特性

- **AI 原生组件**：专为 AI 应用设计的预构建组件
- **基于 shadcn/ui**：构建在 shadcn/ui 之上，保持一致性
- **可定制**：组件代码直接添加到项目中，可完全定制
- **CLI 工具**：通过 CLI 轻松添加组件
- **复合组件架构**：灵活的组件组合
- **TypeScript 支持**：完整的类型定义
- **无障碍设计**：适当的 ARIA 标签和语义化 HTML
- **主题集成**：自动适应项目主题

### 官方文档

- [Vercel AI Elements GitHub 仓库](https://github.com/vercel/ai-elements)
- [Vercel AI SDK 文档](https://vercel.com/docs/ai/openai)
- [AI Elements 组件参考](https://github.com/vercel/ai-elements/blob/main/skills/ai-elements/references/context.md)

## 9. 其他相关技术

### TanStack Query

- **功能**：服务器状态管理
- **官方文档**：[TanStack Query 文档](https://tanstack.com/query/latest)

### Lucide React

- **功能**：图标库
- **官方文档**：[Lucide React 文档](https://lucide.dev)

## 10. 开发工具与最佳实践

### 代码风格

- **ESLint**：代码质量检查
- **Prettier**：代码格式化
- **TypeScript**：类型检查

### 开发命令

- `pnpm dev`：启动开发服务器（使用 TurboPack）
- `pnpm build`：构建生产版本
- `pnpm start`：启动生产服务器
- `pnpm lint`：运行 ESLint
- `pnpm lint:fix`：修复 ESLint 问题
- `pnpm typecheck`：运行 TypeScript 类型检查
- `pnpm check`：同时运行 lint 和 typecheck

## 11. 项目结构参考

```
src/
├── app/                    # Next.js App Router 页面
│   ├── api/                # API 路由
│   ├── workspace/          # 主工作区页面
│   └── mock/               # 模拟/演示页面
├── components/             # React 组件
│   ├── ui/                 # 可复用 UI 组件
│   ├── workspace/          # 工作区特定组件
│   ├── landing/            # 首页组件
│   └── ai-elements/        # AI 相关 UI 元素
├── core/                   # 核心业务逻辑
│   ├── api/                # API 客户端和数据获取
│   ├── artifacts/          # 产物管理
│   ├── config/              # 应用配置
│   ├── i18n/               # 国际化
│   ├── mcp/                # MCP 集成
│   ├── messages/           # 消息处理
│   ├── models/             # 数据模型和类型
│   ├── settings/           # 用户设置
│   ├── skills/             # 技能系统
│   ├── threads/            # 线程管理
│   ├── todos/              # 待办事项系统
│   └── utils/              # 工具函数
├── hooks/                  # 自定义 React hooks
├── lib/                    # 共享库和工具
├── server/                 # 服务器端代码
└── styles/                 # 全局样式
```

## 12. 环境变量配置

```bash
# 后端 API URL（可选，默认使用 nginx 代理）
NEXT_PUBLIC_BACKEND_BASE_URL="http://localhost:8001"
# LangGraph API URL（可选，默认使用 nginx 代理）
NEXT_PUBLIC_LANGGRAPH_BASE_URL="http://localhost:2024"
```

## 13. 浏览器支持

- Chrome 111+
- Edge 111+
- Firefox 111+
- Safari 16.4+

## 14. 系统要求

- Node.js 22+
- pnpm 10.26.2+

***

