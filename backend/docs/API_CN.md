# DeerFlow 后端 API 参考文档

本文档提供 DeerFlow 后端 API 的完整参考。

## 概述

DeerFlow 后端提供两组 API：

1. **LangGraph API** - Agent 交互、线程管理和流式响应（`/api/langgraph/*`）
2. **Gateway API** - 模型、MCP、技能、文件上传和制品管理（`/api/*`）

所有 API 均通过 Nginx 反向代理在 2026 端口访问。

## LangGraph API

基础 URL：`/api/langgraph`

LangGraph API 由 LangGraph 服务器提供，遵循 LangGraph SDK 规范。

### 线程（Threads）

#### 创建线程

```http
POST /api/langgraph/threads
Content-Type: application/json
```

**请求体：**

```json
{
  "metadata": {}
}
```

**响应：**

```json
{
  "thread_id": "abc123",
  "created_at": "2024-01-15T10:30:00Z",
  "metadata": {}
}
```

#### 获取线程状态

```http
GET /api/langgraph/threads/{thread_id}/state
```

**响应：**

```json
{
  "values": {
    "messages": [...],
    "sandbox": {...},
    "artifacts": [...],
    "thread_data": {...},
    "title": "会话标题"
  },
  "next": [],
  "config": {...}
}
```

### 运行（Runs）

#### 创建运行

执行 Agent 并传入输入内容。

```http
POST /api/langgraph/threads/{thread_id}/runs
Content-Type: application/json
```

**请求体：**

```json
{
  "input": {
    "messages": [
      {
        "role": "user",
        "content": "你好，能帮我一下吗？"
      }
    ]
  },
  "config": {
    "configurable": {
      "model_name": "gpt-4",
      "thinking_enabled": false,
      "is_plan_mode": false
    }
  },
  "stream_mode": ["values", "messages-tuple", "custom"]
}
```

**流模式兼容性：**

- 可用：`values`、`messages-tuple`、`custom`、`updates`、`events`、`debug`、`tasks`、`checkpoints`
- 不可用：`tools`（在当前 `langgraph-api` 中已弃用/无效，会触发模式验证错误）

**可配置选项：**

- `model_name`（字符串）：覆盖默认模型
- `thinking_enabled`（布尔值）：为支持的模型启用扩展思考功能
- `is_plan_mode`（布尔值）：启用 TodoList 中间件进行任务跟踪

**响应：** Server-Sent Events (SSE) 流

```
event: values
data: {"messages": [...], "title": "..."}

event: messages
data: {"content": "你好！很高兴为您提供帮助。", "role": "assistant"}

event: end
data: {}
```

#### 获取运行历史

```http
GET /api/langgraph/threads/{thread_id}/runs
```

**响应：**

```json
{
  "runs": [
    {
      "run_id": "run123",
      "status": "success",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### 流式运行

实时流式响应。

```http
POST /api/langgraph/threads/{thread_id}/runs/stream
Content-Type: application/json
```

请求体与创建运行相同。返回 SSE 流。

***

## Gateway API

基础 URL：`/api`

### 模型（Models）

#### 获取模型列表

从配置中获取所有可用的 LLM 模型。

```http
GET /api/models
```

**响应：**

```json
{
  "models": [
    {
      "name": "gpt-4",
      "display_name": "GPT-4",
      "supports_thinking": false,
      "supports_vision": true
    },
    {
      "name": "claude-3-opus",
      "display_name": "Claude 3 Opus",
      "supports_thinking": false,
      "supports_vision": true
    },
    {
      "name": "deepseek-v3",
      "display_name": "DeepSeek V3",
      "supports_thinking": true,
      "supports_vision": false
    }
  ]
}
```

#### 获取模型详情

```http
GET /api/models/{model_name}
```

**响应：**

```json
{
  "name": "gpt-4",
  "display_name": "GPT-4",
  "model": "gpt-4",
  "max_tokens": 4096,
  "supports_thinking": false,
  "supports_vision": true
}
```

### MCP 配置

#### 获取 MCP 配置

获取当前 MCP 服务器配置。

```http
GET /api/mcp/config
```

**响应：**

```json
{
  "mcpServers": {
    "github": {
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "***"
      },
      "description": "GitHub 操作"
    },
    "filesystem": {
      "enabled": false,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "description": "文件系统访问"
    }
  }
}
```

#### 更新 MCP 配置

更新 MCP 服务器配置。

```http
PUT /api/mcp/config
Content-Type: application/json
```

**请求体：**

```json
{
  "mcpServers": {
    "github": {
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "$GITHUB_TOKEN"
      },
      "description": "GitHub 操作"
    }
  }
}
```

**响应：**

```json
{
  "success": true,
  "message": "MCP 配置已更新"
}
```

### 技能（Skills）

#### 获取技能列表

获取所有可用的技能。

```http
GET /api/skills
```

**响应：**

```json
{
  "skills": [
    {
      "name": "pdf-processing",
      "display_name": "PDF 处理",
      "description": "高效处理 PDF 文档",
      "enabled": true,
      "license": "MIT",
      "path": "public/pdf-processing"
    },
    {
      "name": "frontend-design",
      "display_name": "前端设计",
      "description": "设计和构建前端界面",
      "enabled": false,
      "license": "MIT",
      "path": "public/frontend-design"
    }
  ]
}
```

#### 获取技能详情

```http
GET /api/skills/{skill_name}
```

**响应：**

```json
{
  "name": "pdf-processing",
  "display_name": "PDF 处理",
  "description": "高效处理 PDF 文档",
  "enabled": true,
  "license": "MIT",
  "path": "public/pdf-processing",
  "allowed_tools": ["read_file", "write_file", "bash"],
  "content": "# PDF 处理\n\nAgent 指令..."
}
```

#### 启用技能

```http
POST /api/skills/{skill_name}/enable
```

**响应：**

```json
{
  "success": true,
  "message": "技能 'pdf-processing' 已启用"
}
```

#### 禁用技能

```http
POST /api/skills/{skill_name}/disable
```

**响应：**

```json
{
  "success": true,
  "message": "技能 'pdf-processing' 已禁用"
}
```

#### 安装技能

从 `.skill` 文件安装技能。

```http
POST /api/skills/install
Content-Type: multipart/form-data
```

**请求体：**

- `file`：要安装的 `.skill` 文件

**响应：**

```json
{
  "success": true,
  "message": "技能 'my-skill' 安装成功",
  "skill": {
    "name": "my-skill",
    "display_name": "我的技能",
    "path": "custom/my-skill"
  }
}
```

### 文件上传

#### 上传文件

向线程上传一个或多个文件。

```http
POST /api/threads/{thread_id}/uploads
Content-Type: multipart/form-data
```

**请求体：**

- `files`：一个或多个要上传的文件

**响应：**

```json
{
  "success": true,
  "files": [
    {
      "filename": "document.pdf",
      "size": 1234567,
      "path": ".deer-flow/threads/abc123/user-data/uploads/document.pdf",
      "virtual_path": "/mnt/user-data/uploads/document.pdf",
      "artifact_url": "/api/threads/abc123/artifacts/mnt/user-data/uploads/document.pdf",
      "markdown_file": "document.md",
      "markdown_path": ".deer-flow/threads/abc123/user-data/uploads/document.md",
      "markdown_virtual_path": "/mnt/user-data/uploads/document.md",
      "markdown_artifact_url": "/api/threads/abc123/artifacts/mnt/user-data/uploads/document.md"
    }
  ],
  "message": "成功上传 1 个文件"
}
```

**支持的文档格式**（自动转换为 Markdown）：

- PDF（`.pdf`）
- PowerPoint（`.ppt`、`.pptx`）
- Excel（`.xls`、`.xlsx`）
- Word（`.doc`、`.docx`）

#### 获取已上传文件列表

```http
GET /api/threads/{thread_id}/uploads/list
```

**响应：**

```json
{
  "files": [
    {
      "filename": "document.pdf",
      "size": 1234567,
      "path": ".deer-flow/threads/abc123/user-data/uploads/document.pdf",
      "virtual_path": "/mnt/user-data/uploads/document.pdf",
      "artifact_url": "/api/threads/abc123/artifacts/mnt/user-data/uploads/document.pdf",
      "extension": ".pdf",
      "modified": 1705997600.0
    }
  ],
  "count": 1
}
```

#### 删除文件

```http
DELETE /api/threads/{thread_id}/uploads/{filename}
```

**响应：**

```json
{
  "success": true,
  "message": "已删除 document.pdf"
}
```

### 制品（Artifacts）

#### 获取制品

下载或查看 Agent 生成的制品。

```http
GET /api/threads/{thread_id}/artifacts/{path}
```

**路径示例：**

- `/api/threads/abc123/artifacts/mnt/user-data/outputs/result.txt`
- `/api/threads/abc123/artifacts/mnt/user-data/uploads/document.pdf`

**查询参数：**

- `download`（布尔值）：如果为 `true`，强制下载并添加 Content-Disposition 响应头

**响应：** 带有适当 Content-Type 的文件内容

***

## 错误响应

所有 API 以统一格式返回错误：

```json
{
  "detail": "描述错误的错误信息"
}
```

**HTTP 状态码：**

- `400` - 错误请求：无效输入
- `404` - 未找到：资源不存在
- `422` - 验证错误：请求验证失败
- `500` - 内部服务器错误：服务器端错误

***

## 身份认证

目前，DeerFlow 未实现身份认证。所有 API 均无需凭据即可访问。

注意：这是指 DeerFlow API 的身份认证。MCP 出站连接仍可为已配置的 HTTP/SSE MCP 服务器使用 OAuth。

对于生产环境部署，建议：

1. 使用 Nginx 进行基础认证或 OAuth 集成
2. 部署在 VPN 或私有网络之后
3. 实现自定义身份认证中间件

***

## 速率限制

默认未实现速率限制。对于生产环境部署，可在 Nginx 中配置速率限制：

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://backend;
}
```

***

## WebSocket 支持

LangGraph 服务器支持 WebSocket 连接进行实时流式传输。连接地址：

```
ws://localhost:2026/api/langgraph/threads/{thread_id}/runs/stream
```

***

## SDK 使用

### Python（LangGraph SDK）

```python
from langgraph_sdk import get_client

client = get_client(url="http://localhost:2026/api/langgraph")

# 创建线程
thread = await client.threads.create()

# 运行 Agent
async for event in client.runs.stream(
    thread["thread_id"],
    "lead_agent",
    input={"messages": [{"role": "user", "content": "你好"}]},
    config={"configurable": {"model_name": "gpt-4"}},
    stream_mode=["values", "messages-tuple", "custom"],
):
    print(event)
```

### JavaScript/TypeScript

```typescript
// 使用 fetch 调用 Gateway API
const response = await fetch('/api/models');
const data = await response.json();
console.log(data.models);

// 使用 EventSource 进行流式传输
const eventSource = new EventSource(
  `/api/langgraph/threads/${threadId}/runs/stream`
);
eventSource.onmessage = (event) => {
  console.log(JSON.parse(event.data));
};
```

### cURL 示例

```bash
# 获取模型列表
curl http://localhost:2026/api/models

# 获取 MCP 配置
curl http://localhost:2026/api/mcp/config

# 上传文件
curl -X POST http://localhost:2026/api/threads/abc123/uploads \
  -F "files=@document.pdf"

# 启用技能
curl -X POST http://localhost:2026/api/skills/pdf-processing/enable

# 创建线程并运行 Agent
curl -X POST http://localhost:2026/api/langgraph/threads \
  -H "Content-Type: application/json" \
  -d '{}'

curl -X POST http://localhost:2026/api/langgraph/threads/abc123/runs \
  -H "Content-Type: application/json" \
  -d '{
    "input": {"messages": [{"role": "user", "content": "你好"}]},
    "config": {"configurable": {"model_name": "gpt-4"}}
  }'
```

