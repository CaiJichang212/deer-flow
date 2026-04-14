# Nginx代理访问后端服务全流程

本文档详细说明 DeerFlow 项目中，从前端页面点击触发请求，经过 Nginx 代理，最终到达后端服务的完整全链路调用流程。

## 1. 整体架构 (Architecture)

```
┌─────────────┐      ┌─────────────┐      ┌────────────────┐
│  前端应用    │ ────▶│  Nginx 代理  │ ────▶│  后端服务集群    │
│ (Next.js)   │      │ (Port 2026) │      │ (Gateway/LLM)  │
└─────────────┘      └─────────────┘      └────────────────┘
                               │
                               ▼
                    ┌───────────────────┐
                    │  上游服务器配置     │
                    │ ┌───────────────┐ │
                    │ │ gateway:8001  │ │
                    │ ├───────────────┤ │
                    │ │ langgraph:2024│ │
                    │ └───────────────┘ │
                    └───────────────────┘
```

## 2. 全链路调用流程 (Full Link Call Flow)

以“加载模型列表”请求为例：

### 第一步：前端发起请求 (Frontend Request)
- **触发逻辑**: 在 [src/core/models/api.ts](file:///Users/lzc/TNTprojectZ/deer-flow/frontend/src/core/models/api.ts) 中执行 `fetch("/api/models")`。
- **配置支撑**: [src/core/config/index.ts](file:///Users/lzc/TNTprojectZ/deer-flow/frontend/src/core/config/index.ts) 中的 `getBackendBaseURL()` 默认返回空字符串 `""`，使请求成为相对路径。
- **浏览器行为**: 浏览器补全当前 Origin (如 `http://localhost:2026`)，发出真实请求：`GET http://localhost:2026/api/models`。

### 第二步：Nginx 接收并转发 (Nginx Proxy)
- **监听端点**: Nginx 监听在 **2026 端口**。
- **匹配规则**:
    - 路径匹配到 `location /api/models`。
    - **转发目标**: 代理到 `http://gateway` (即 `127.0.0.1:8001`)。
- **CORS 处理**: Nginx 自动添加 `Access-Control-Allow-Origin: *` 头，屏蔽后端服务的跨域限制。

### 第三步：后端 Gateway 处理 (Backend Handling)
- **接收服务**: [app.py](file:///Users/lzc/TNTprojectZ/deer-flow/backend/app/gateway/app.py) 初始化在 **8001 端口** 的 FastAPI 应用。
- **路由分发**: 请求被分发至 [models.py](file:///Users/lzc/TNTprojectZ/deer-flow/backend/app/gateway/routers/models.py) 的 `list_models` 函数。
- **业务执行**: 读取系统配置中的模型列表，通过 Pydantic 序列化为 JSON 返回。

### 第四步：响应返回 (Response Return)
- **路径**: Gateway (8001) -> Nginx (2026) -> 浏览器。
- **UI 更新**: 前端解析 JSON 数据，渲染模型下拉框。

---

## 3. Nginx 代理逻辑详解

### 3.1 路由规则表

| 路径匹配                 | 转发目标                | 说明                                    |
| :----------------------- | :---------------------- | :-------------------------------------- |
| `/api/langgraph/`        | `http://langgraph:2024` | 核心 AI 执行，需要去掉前缀并开启流式    |
| `/api/models`            | `http://gateway:8001`   | 模型配置查询                            |
| `/api/agents`            | `http://gateway:8001`   | Agent CRUD 管理                         |
| `/api/mcp`               | `http://gateway:8001`   | MCP 协议服务器配置                      |
| `/api/threads/*/uploads` | `http://gateway:8001`   | 文件上传，需配置 `client_max_body_size` |
| `/`                      | `http://frontend:3000`  | 前端静态页面和 Next.js 服务             |

### 3.2 关键 Nginx 指令
- **`proxy_buffering off;`**: 针对 LangGraph API (2024) 必须关闭缓冲，确保 AI 的打字机效果（流式响应）能实时到达前端。
- **`rewrite ^/api/langgraph/(.*) /$1 break;`**: 剥离内部网关前缀，适配后端服务。

---

## 4. 前端基础 URL 逻辑

在 [src/core/config/index.ts](file:///Users/lzc/TNTprojectZ/deer-flow/frontend/src/core/config/index.ts) 中定义了自动寻址逻辑：

```typescript
export function getBackendBaseURL() {
  // 如果环境变量未定义，返回空字符串，请求将走 Nginx 代理端口
  return env.NEXT_PUBLIC_BACKEND_BASE_URL || "";
}

export function getLangGraphBaseURL() {
  // LangGraph SDK 需要完整 URL，从当前 origin 构造
  if (typeof window !== "undefined") {
    return `${window.location.origin}/api/langgraph`;
  }
  return "http://localhost:2026/api/langgraph";
}
```

---

## 5. 优势总结

1. **统一端口**: 所有请求通过 2026 端口，前端代码无需感知多后端端口的存在。
2. **中心化跨域**: 由 Nginx 统一处理 CORS，后端 API 服务无需在代码层面手动配置跨域头。
3. **安全隔离**: 后端 8001 和 2024 端口可不对外网暴露，仅允许 Nginx 本地转发。
4. **性能透明**: 自动处理流式响应缓存和超时重连。

## 6. 故障排查 (Troubleshooting)

- **502 Bad Gateway**: 检查后端服务 (8001/2024) 是否已启动。
- **CORS Error**: 检查 Nginx 配置文件是否正确添加了 `Access-Control-Allow-Origin`。
- **流式卡顿**: 确认 `proxy_buffering` 是否在对应的 `location` 块中被设为 `off`。

---
*最后更新日期: 2026-03-30*
