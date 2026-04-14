# DeerFlow 后端

DeerFlow 是一个基于 LangGraph 的 AI 超级Agent，具有沙盒执行、持久内存和可扩展的工具集成能力。后端使 AI Agent能够执行代码、浏览网页、管理文件、将任务委托给子Agent，并在对话中保留上下文 - 所有这些都在隔离的、每线程环境中进行。

---

## 架构

```
                        ┌──────────────────────────────────────┐
                        │          Nginx (端口 2026)            │
                        │          统一反向代理                  │
                        └───────┬──────────────────┬───────────┘
                                │                  │
              /api/langgraph/*  │                  │  /api/* (其他)
                                ▼                  ▼
               ┌────────────────────┐  ┌────────────────────────┐
               │ LangGraph 服务器   │  │   网关 API (8001)      │
               │    (端口 2024)     │  │   FastAPI REST         │
               │                    │  │                        │
               │ ┌────────────────┐ │  │ 模型、MCP、技能、      │
               │ │  主Agent        │ │  │ 内存、上传、           │
               │ │  ┌──────────┐  │ │  │ 产物                  │
               │ │  │ 中间件    │  │ │  └────────────────────────┘
               │ │  │  链      │  │ │
               │ │  └──────────┘  │ │
               │ │  ┌──────────┐  │ │
               │ │  │  工具    │  │ │
               │ │  └──────────┘  │ │
               │ │  ┌──────────┐  │ │
               │ │  │ 子Agent   │  │ │
               │ │  └──────────┘  │ │
               │ └────────────────┘ │
               └────────────────────┘
```

**请求路由**（通过 Nginx）：
- `/api/langgraph/*` → LangGraph 服务器 - Agent交互、线程、流式传输
- `/api/*`（其他）→ 网关 API - 模型、MCP、技能、内存、产物、上传
- `/`（非 API）→ 前端 - Next.js 网页界面

---

## 核心组件

### 主Agent

单个 LangGraph Agent（`lead_agent`）是运行时入口点，通过 `make_lead_agent(config)` 创建。它结合了：

- **动态模型选择**，支持思考和视觉能力
- **中间件链**，用于处理横切关注点（9 个中间件）
- **工具系统**，包含沙盒、MCP、社区和内置工具
- **子Agent委托**，用于并行任务执行
- **系统提示**，包含技能注入、内存上下文和工作目录指导

### 中间件链

中间件按严格顺序执行，每个中间件处理特定关注点：

| # | 中间件 | 用途 |
|---|-------|------|
| 1 | **ThreadDataMiddleware** | 创建每线程隔离目录（工作区、上传、输出） |
| 2 | **UploadsMiddleware** | 将新上传的文件注入对话上下文 |
| 3 | **SandboxMiddleware** | 获取用于代码执行的沙盒环境 |
| 4 | **SummarizationMiddleware** | 接近令牌限制时减少上下文（可选） |
| 5 | **TodoListMiddleware** | 在计划模式下跟踪多步骤任务（可选） |
| 6 | **TitleMiddleware** | 首次交换后自动生成对话标题 |
| 7 | **MemoryMiddleware** | 将对话排队以进行异步内存提取 |
| 8 | **ViewImageMiddleware** | 为支持视觉的模型注入图像数据（条件性） |
| 9 | **ClarificationMiddleware** | 拦截澄清请求并中断执行（必须是最后一个） |

### 沙盒系统

每线程隔离执行，带有虚拟路径转换：

- **抽象接口**：`execute_command`、`read_file`、`write_file`、`list_dir`
- **提供者**：`LocalSandboxProvider`（文件系统）和 `AioSandboxProvider`（Docker，位于 community/ 中）
- **虚拟路径**：`/mnt/user-data/{workspace,uploads,outputs}` → 线程特定的物理目录
- **技能路径**：`/mnt/skills` → `deer-flow/skills/` 目录
- **技能加载**：递归发现 `skills/{public,custom}` 下的嵌套 `SKILL.md` 文件并保留嵌套容器路径
- **工具**：`bash`、`ls`、`read_file`、`write_file`、`str_replace`

### 子Agent系统

异步任务委托，支持并发执行：

- **内置Agent**：`general-purpose`（完整工具集）和 `bash`（命令专家）
- **并发**：每轮最多 3 个子Agent，15 分钟超时
- **执行**：后台线程池，带有状态跟踪和 SSE 事件
- **流程**：Agent调用 `task()` 工具 → 执行器在后台运行子Agent → 轮询完成 → 返回结果

### 内存系统

由 LLM 驱动的跨对话持久上下文保留：

- **自动提取**：分析对话以获取用户上下文、事实和偏好
- **结构化存储**：用户上下文（工作、个人、首要）、历史记录和带置信度评分的事实
- **防抖更新**：批处理更新以最小化 LLM 调用（可配置等待时间）
- **系统提示注入**：将顶级事实和上下文注入Agent提示
- **存储**：带有基于修改时间的缓存失效的 JSON 文件

### 工具生态系统

| 类别 | 工具 |
|------|------|
| **沙盒** | `bash`、`ls`、`read_file`、`write_file`、`str_replace` |
| **内置** | `present_files`、`ask_clarification`、`view_image`、`task`（子Agent） |
| **社区** | Tavily（网络搜索）、Jina AI（网络获取）、Firecrawl（抓取）、DuckDuckGo（图像搜索） |
| **MCP** | 任何模型上下文协议服务器（stdio、SSE、HTTP 传输） |
| **技能** | 通过系统提示注入的领域特定工作流 |

### 网关 API

提供 REST 端点以实现前端集成的 FastAPI 应用：

| 路由 | 用途 |
|------|------|
| `GET /api/models` | 列出可用的 LLM 模型 |
| `GET/PUT /api/mcp/config` | 管理 MCP 服务器配置 |
| `GET/PUT /api/skills` | 列出和管理技能 |
| `POST /api/skills/install` | 从 `.skill` 归档安装技能 |
| `GET /api/memory` | 检索内存数据 |
| `POST /api/memory/reload` | 强制重新加载内存 |
| `GET /api/memory/config` | 内存配置 |
| `GET /api/memory/status` | 组合配置 + 数据 |
| `POST /api/threads/{id}/uploads` | 上传文件（自动将 PDF/PPT/Excel/Word 转换为 Markdown，拒绝目录路径） |
| `GET /api/threads/{id}/uploads/list` | 列出上传的文件 |
| `GET /api/threads/{id}/artifacts/{path}` | 提供生成的产物 |

### 即时通讯通道

IM 桥接支持飞书、Slack 和 Telegram。Slack 和 Telegram 仍然使用最终的 `runs.wait()` 响应路径，而飞书现在通过 `runs.stream(["messages-tuple", "values"])` 进行流式传输，并在原地更新单个线程卡片。

对于飞书卡片更新，DeerFlow 为每个入站消息存储运行中卡片的 `message_id`，并在运行完成前修补同一张卡片，保留现有的 `OK` / `DONE` 反应流程。

---

## 快速开始

### 前置条件

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 包管理器
- 所选 LLM 提供商的 API 密钥

### 安装

```bash
cd deer-flow

# 复制配置文件
cp config.example.yaml config.yaml

# 安装后端依赖
cd backend
make install
```

### 配置

编辑项目根目录中的 `config.yaml`：

```yaml
models:
  - name: gpt-4o
    display_name: GPT-4o
    use: langchain_openai:ChatOpenAI
    model: gpt-4o
    api_key: $OPENAI_API_KEY
    supports_thinking: false
    supports_vision: true
```

设置 API 密钥：

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 运行

**完整应用**（从项目根目录）：

```bash
make dev  # 启动 LangGraph + 网关 + 前端 + Nginx
```

访问地址：http://localhost:2026

**仅后端**（从后端目录）：

```bash
# 终端 1：LangGraph 服务器
make dev

# 终端 2：网关 API
make gateway
```

直接访问：LangGraph 在 http://localhost:2024，网关在 http://localhost:8001

---

## 项目结构

```
backend/
├── src/
│   ├── agents/                  # Agent系统
│   │   ├── lead_agent/         # 主Agent（工厂、提示）
│   │   ├── middlewares/        # 9 个中间件组件
│   │   ├── memory/             # 内存提取和存储
│   │   └── thread_state.py    # ThreadState 模式
│   ├── gateway/                # FastAPI 网关 API
│   │   ├── app.py             # 应用设置
│   │   └── routers/           # 6 个路由模块
│   ├── sandbox/                # 沙盒执行
│   │   ├── local/             # 本地文件系统提供者
│   │   ├── sandbox.py         # 抽象接口
│   │   ├── tools.py           # bash、ls、read/write/
│   │   └── middleware.py      # 沙盒生命周期
│   ├── subagents/              # 子Agent委托
│   │   ├── builtins/          # general-purpose、bash Agent
│   │   ├── executor.py        # 后台执行引擎
│   │   └── registry.py        # Agent注册表
│   ├── tools/builtins/         # 内置工具
│   ├── mcp/                    # MCP 协议集成
│   ├── models/                 # 模型工厂
│   ├── skills/                 # 技能发现和加载
│   ├── config/                 # 配置系统
│   ├── community/              # 社区工具和提供者
│   ├── reflection/             # 动态模块加载
│   └── utils/                  # 工具函数
├── docs/                       # 文档
├── tests/                      # 测试套件
├── langgraph.json              # LangGraph 服务器配置
├── pyproject.toml              # Python 依赖
├── Makefile                    # 开发命令
└── Dockerfile                  # 容器构建
```

---

## 配置

### 主配置（`config.yaml`）

放置在项目根目录。以 `$` 开头的配置值解析为环境变量。

关键部分：
- `models` - 带有类路径、API 密钥、思考/视觉标志的 LLM 配置
- `tools` - 带有模块路径和组的工具定义
- `tool_groups` - 逻辑工具分组
- `sandbox` - 执行环境提供者
- `skills` - 技能目录路径
- `title` - 自动标题生成设置
- `summarization` - 上下文摘要设置
- `subagents` - 子Agent系统（启用/禁用）
- `memory` - 内存系统设置（启用、存储、防抖、事实限制）

提供者说明：
- `models[*].use` 通过模块路径引用提供者类（例如 `langchain_openai:ChatOpenAI`）。
- 如果缺少提供者模块，DeerFlow 现在会返回带有安装指导的可操作错误（例如 `uv add langchain-google-genai`）。

### 扩展配置（`extensions_config.json`）

单个文件中的 MCP 服务器和技能状态：

```json
{
  "mcpServers": {
    "github": {
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"}
    },
    "secure-http": {
      "enabled": true,
      "type": "http",
      "url": "https://api.example.com/mcp",
      "oauth": {
        "enabled": true,
        "token_url": "https://auth.example.com/oauth/token",
        "grant_type": "client_credentials",
        "client_id": "$MCP_OAUTH_CLIENT_ID",
        "client_secret": "$MCP_OAUTH_CLIENT_SECRET"
      }
    }
  },
  "skills": {
    "pdf-processing": {"enabled": true}
  }
}
```

### 环境变量

- `DEER_FLOW_CONFIG_PATH` - 覆盖 config.yaml 位置
- `DEER_FLOW_EXTENSIONS_CONFIG_PATH` - 覆盖 extensions_config.json 位置
- 模型 API 密钥：`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`DEEPSEEK_API_KEY` 等
- 工具 API 密钥：`TAVILY_API_KEY`、`GITHUB_TOKEN` 等

---

## 开发

### 命令

```bash
make install    # 安装依赖
make dev        # 运行 LangGraph 服务器（端口 2024）
make gateway    # 运行网关 API（端口 8001）
make lint       # 运行 linter（ruff）
make format     # 格式化代码（ruff）
```

### 代码风格

- **Linter/格式化工具**：`ruff`
- **行长度**：240 字符
- **Python**：3.12+ 带有类型提示
- **引号**：双引号
- **缩进**：4 个空格

### 测试

```bash
uv run pytest
```

---

## 技术栈

- **LangGraph** (1.0.6+) - Agent框架和多Agent编排
- **LangChain** (1.2.3+) - LLM 抽象和工具系统
- **FastAPI** (0.115.0+) - 网关 REST API
- **langchain-mcp-adapters** - 模型上下文协议支持
- **agent-sandbox** - 沙盒代码执行
- **markitdown** - 多格式文档转换
- **tavily-python** / **firecrawl-py** - 网络搜索和抓取

---

## 文档

- [配置指南](docs/CONFIGURATION.md)
- [架构详情](docs/ARCHITECTURE.md)
- [API 参考](docs/API.md)
- [文件上传](docs/FILE_UPLOAD.md)
- [路径示例](docs/PATH_EXAMPLES.md)
- [上下文摘要](docs/summarization.md)
- [计划模式](docs/plan_mode_usage.md)
- [设置指南](docs/SETUP.md)

---

## 许可证

请参阅项目根目录中的 [LICENSE](../LICENSE) 文件。

## 贡献

请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献指南。