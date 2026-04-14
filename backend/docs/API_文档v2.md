# 项目后端 API 参考文档

## 概述

项目后端提供两组 API：

1. **智能体 API** - Agent 交互、线程管理和流式响应（`/api/agent/*`）
2. **其他功能 API** - 模型、MCP（`/api/*`）

## 智能体 API

基础 URL：`/api/agent`

### 线程（Threads）

#### 创建线程

```http
POST /api/agent/threads
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
GET /api/agent/threads/{thread_id}/state
```

**响应：**

```json
{
  "values": {
    "messages": [...],
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
POST /api/agent/threads/{thread_id}/runs
Content-Type: application/json
```

**请求体：**

**可配置选项：**

- `model_name`（字符串）：覆盖默认模型
- `thinking_enabled`（布尔值）：为支持的模型启用扩展思考功能


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
GET /api/agent/threads/{thread_id}/runs
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
POST /api/agent/threads/{thread_id}/runs/stream
Content-Type: application/json
```

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
  "mcp_settings": {
    "servers": {
      "mysql": {
        "transport": "streamable_http",
        "url": "http://localhost:31002/mcp/",
        "enabled_tools": [
          "is_in_shanghai",
          "check_utalk_identity",
          "check_nickname_pattern",
          "check_friend_pattern",
          "check_age_anomaly",
          "check_night_owl",
          "check_hotel_stays",
          "check_gender_anomaly",
          "analyze_role"
        ]
      }
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
  "mcp_settings": {
    "servers": {
      "mysql_new": {
        "transport": "streamable_http",
        "url": "http://localhost:31002/mcp/",
        "enabled_tools": [
          "is_in_shanghai",
          "check_utalk_identity",
          "check_nickname_pattern",
          "check_friend_pattern",
          "check_age_anomaly",
          "check_night_owl",
          "check_hotel_stays",
          "check_gender_anomaly",
          "analyze_role"
        ]
      }
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


***

## 接口使用
### cURL 示例

```bash
# 获取模型列表
curl http://localhost:2026/api/models

# 获取 MCP 配置
curl http://localhost:2026/api/mcp/config


# 创建线程并运行 Agent
curl -X POST http://localhost:2026/api/agent/threads \
  -H "Content-Type: application/json" \
  -d '{}'

curl -X POST http://localhost:2026/api/agent/threads/abc123/runs \
  -H "Content-Type: application/json" \
  -d '{
    "input": {"messages": [{"role": "user", "content": "你好"}]},
    "config": {"configurable": {"model_name": "gpt-4"}}
  }'
```

