# 项目后端 API 参考文档

## 概述

项目后端提供两组 API：

1. **智能体 API** - Agent 交互、线程管理和流式响应（`/api/langgraph/*`）
2. **Gateway API** - 模型、MCP（`/api/*`）

所有 API 均通过 Nginx 反向代理在 2026 端口访问。

## 智能体 API

基础 URL：`/api/langgraph`

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

**可配置选项：**

- `model_name`（字符串）：覆盖默认模型
- `thinking_enabled`（布尔值）：为支持的模型启用扩展思考功能

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

## 其他API

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

<br />

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

