# DeerFlow 前端


## 技术栈

- **框架**：[Next.js 16](https://nextjs.org/) 搭配 [App Router](https://nextjs.org/docs/app)
- **UI**：[React 19](https://react.dev/)、[Tailwind CSS 4](https://tailwindcss.com/)、[Shadcn UI](https://ui.shadcn.com/)、[MagicUI](https://magicui.design/) 和 [React Bits](https://reactbits.dev/)
- **AI 集成**：[LangGraph SDK](https://www.npmjs.com/package/@langchain/langgraph-sdk) 和 [Vercel AI Elements](https://vercel.com/ai-sdk/ai-elements)

## 快速开始

### 前提条件

- Node.js 22+
- pnpm 10.26.2+

### 安装

```bash
# 安装依赖
pnpm install

# 复制环境变量
cp .env.example .env
# 编辑 .env 文件配置你的设置
```

### 开发

```bash
# 启动开发服务器
pnpm dev

# 应用将在 http://localhost:3000 可用
```

### 构建

```bash
# 类型检查
pnpm typecheck

# 代码检查
pnpm lint

# 构建生产版本
pnpm build

# 启动生产服务器
pnpm start
```

## 站点地图

```
├── /                    # 首页
├── /chats               # 聊天列表
├── /chats/new           # 新建聊天页面
└── /chats/[thread_id]   # 特定聊天页面
```

## 配置

### 环境变量

关键环境变量（完整列表见 `.env.example`）：

```bash
# 后端 API URL（可选，默认使用 nginx 代理）
NEXT_PUBLIC_BACKEND_BASE_URL="http://localhost:8001"
# LangGraph API URL（可选，默认使用 nginx 代理）
NEXT_PUBLIC_LANGGRAPH_BASE_URL="http://localhost:2024"
```

## 项目结构

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
├── server/                 # 服务器端代码（尚未可用）
│   └── better-auth/        # 身份验证设置（尚未可用）
└── styles/                 # 全局样式
```

## 脚本

| 命令 | 描述 |
|---------|-------------|
| `pnpm dev` | 使用 Turbopack 启动开发服务器 |
| `pnpm build` | 构建生产版本 |
| `pnpm start` | 启动生产服务器 |
| `pnpm lint` | 运行 ESLint |
| `pnpm lint:fix` | 修复 ESLint 问题 |
| `pnpm typecheck` | 运行 TypeScript 类型检查 |
| `pnpm check` | 同时运行 lint 和 typecheck |

## 开发说明

- 使用 pnpm workspaces（详见 package.json 中的 `packageManager`）
- 开发环境默认启用 Turbopack 以加快构建速度
- 可使用 `SKIP_ENV_VALIDATION=1` 跳过环境验证（对 Docker 有用）
- 后端 API URL 是可选的；开发环境默认使用 nginx 代理

## 许可证

MIT 许可证。详情请见 [LICENSE](../LICENSE)。