# DeerFlow Harness 项目解读文档

## 目录

1. [项目架构概述](#项目架构概述)
2. [核心模块功能说明](#核心模块功能说明)
3. [关键代码逻辑分析](#关键代码逻辑分析)
4. [接口设计文档](#接口设计文档)
5. [数据流程说明](#数据流程说明)
6. [开发规范](#开发规范)

---

## 项目架构概述

### 1. 项目定位

DeerFlow Harness 是一个基于 LangChain 和 LangGraph 构建的Agent系统框架。它提供了一个可扩展的、模块化的Agent架构，支持：

- **多模型支持**：灵活配置多种 LLM 模型（OpenAI、Anthropic、DeepSeek 等）
- **沙箱环境**：安全的代码执行和文件操作环境
- **子Agent系统**：支持任务委托和并行执行
- **MCP 协议**：集成 Model Context Protocol 扩展工具生态
- **技能系统**：可插拔的技能模块扩展
- **持久化存储**：支持内存、SQLite、PostgreSQL 多种存储后端

### 2. 目录结构

```
deerflow/
├── agents/                    # Agent核心模块
│   ├── checkpointer/          # 状态持久化
│   ├── lead_agent/            # 主Agent实现
│   ├── memory/                # 记忆系统
│   └── middlewares/           # 中间件链
├── community/                 # 社区集成工具
│   ├── aio_sandbox/           # 异步沙箱
│   ├── firecrawl/             # 网页抓取
│   ├── image_search/          # 图像搜索
│   ├── infoquest/             # 信息查询
│   ├── jina_ai/               # Jina AI 集成
│   └── tavily/                # Tavily 搜索
├── config/                    # 配置管理
├── mcp/                       # MCP 协议实现
├── models/                    # 模型工厂
├── reflection/                # 反射解析器
├── sandbox/                   # 沙箱环境
│   └── local/                 # 本地沙箱实现
├── skills/                    # 技能系统
├── subagents/                 # 子Agent系统
├── tools/                     # 工具定义
├── utils/                     # 工具函数
└── client.py                  # 客户端入口
```

### 3. 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        DeerFlowClient                           │
│  ( Python 客户端 / LangGraph Server / Gateway API)               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Lead Agent                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Middleware Chain                     │    │
│  │  ThreadData → Sandbox → Uploads → DanglingToolCall      │    │
│  │  → ToolErrorHandling → Summarization → Todo → Title     │    │
│  │  → Memory → ViewImage → SubagentLimit → LoopDetection   │    │
│  │  → Clarification                                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      Tools Layer                        │    │
│  │  Builtin Tools │ MCP Tools │ Skills │ Subagent Tools    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Sandbox Layer                            │
│                    LocalSandbox (本地执行)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心模块功能说明

### 1. Agents 模块

#### 1.1 Lead Agent（主Agent）

**位置**: [agents/lead_agent/](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/)

**核心职责**：
- 构建和配置主Agent实例
- 管理中间件链
- 生成系统提示词

**关键文件**：

| 文件 | 功能 |
|------|------|
| [agent.py](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py) | Agent创建和中间件构建 |
| [prompt.py](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/prompt.py) | 系统提示词模板 |

**核心函数**：

```python
def make_lead_agent(config: RunnableConfig):
    """创建主Agent实例"""
    # 解析模型配置
    # 构建中间件链
    # 创建Agent
```

#### 1.2 Checkpointer（状态持久化）

**位置**: [agents/checkpointer/](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/agents/checkpointer/)

**支持的存储后端**：
- `memory`: 内存存储（非持久化）
- `sqlite`: SQLite 数据库
- `postgres`: PostgreSQL 数据库

**使用方式**：

```python
# 同步方式
from deerflow.agents.checkpointer.provider import get_checkpointer
checkpointer = get_checkpointer()

# 异步方式
from deerflow.agents.checkpointer.async_provider import make_checkpointer
async with make_checkpointer() as checkpointer:
    # 使用 checkpointer
```

#### 1.3 Memory（记忆系统）

**位置**: [agents/memory/](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/agents/memory/)

**功能**：
- 跨会话记忆持久化
- 自动记忆更新（基于 LLM 总结）
- 防抖队列机制

**记忆结构**：

```json
{
  "version": "1.0",
  "lastUpdated": "2024-01-01T00:00:00Z",
  "user": {
    "workContext": {"summary": "", "updatedAt": ""},
    "personalContext": {"summary": "", "updatedAt": ""},
    "topOfMind": {"summary": "", "updatedAt": ""}
  },
  "history": {
    "recentMonths": {"summary": "", "updatedAt": ""},
    "earlierContext": {"summary": "", "updatedAt": ""},
    "longTermBackground": {"summary": "", "updatedAt": ""}
  },
  "facts": []
}
```

#### 1.4 Middlewares（中间件）

**位置**: [agents/middlewares/](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/agents/middlewares/)

**完整中间件列表**：

| 中间件 | 功能 | 执行阶段 |
|--------|------|----------|
| ThreadDataMiddleware | 创建线程数据目录 | before_agent |
| SandboxMiddleware | 创建沙箱环境 | before_agent |
| UploadsMiddleware | 注入上传文件信息 | before_agent |
| DanglingToolCallMiddleware | 修复悬挂的工具调用 | wrap_model_call |
| ToolErrorHandlingMiddleware | 工具错误处理 | wrap_tool_call |
| SummarizationMiddleware | 对话历史摘要 | 中间件链 |
| TodoMiddleware | 任务列表管理（计划模式） | 中间件链 |
| TitleMiddleware | 自动生成标题 | after_model |
| MemoryMiddleware | 记忆更新队列 | after_agent |
| ViewImageMiddleware | 图像查看处理 | after_model |
| SubagentLimitMiddleware | 子Agent并发限制 | 中间件链 |
| LoopDetectionMiddleware | 循环检测 | 中间件链 |
| ClarificationMiddleware | 澄清请求拦截 | wrap_tool_call |

**中间件构建顺序**（来自 `_build_middlewares` 函数）：

```python
# 1. 基础运行时中间件（来自 build_lead_runtime_middlewares）
middlewares = [
    ThreadDataMiddleware,      # 线程数据目录
    SandboxMiddleware,         # 沙箱环境
    UploadsMiddleware,         # 上传文件
    DanglingToolCallMiddleware,# 悬挂工具调用修复
    ToolErrorHandlingMiddleware,# 工具错误处理
]

# 2. 可选中间件
if enabled: middlewares.append(SummarizationMiddleware)  # 摘要
if plan_mode: middlewares.append(TodoMiddleware)         # 任务列表

# 3. 后续中间件
middlewares.append(TitleMiddleware)                       # 标题生成
middlewares.append(MemoryMiddleware)                      # 记忆更新
if supports_vision: middlewares.append(ViewImageMiddleware)  # 图像查看
if subagent_enabled: middlewares.append(SubagentLimitMiddleware)  # 子Agent限制
middlewares.append(LoopDetectionMiddleware)               # 循环检测
middlewares.append(ClarificationMiddleware)               # 澄清拦截
```

### 2. Config 模块

**位置**: [config/](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/config/)

**配置文件结构**：

| 文件 | 配置内容 |
|------|----------|
| [app_config.py](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/config/app_config.py) | 主配置类 |
| [model_config.py](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/config/model_config.py) | 模型配置 |
| [paths.py](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/config/paths.py) | 路径配置 |
| [agents_config.py](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/config/agents_config.py) | 自定义Agent配置 |

**配置加载优先级**：

1. 显式指定的配置路径
2. `DEER_FLOW_CONFIG_PATH` 环境变量
3. 当前目录的 `config.yaml`
4. 父目录的 `config.yaml`

### 3. Sandbox 模块

**位置**: [sandbox/](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/sandbox/)

**架构**：

```
Sandbox (抽象基类)
    │
    └── LocalSandbox    (本地执行 - 当前唯一实现)
```

> **注意**：当前版本仅实现了 `LocalSandbox`，没有 `DockerSandbox` 或 `RemoteSandbox` 实现。沙箱通过 `SandboxMiddleware` 进行管理。

**虚拟路径映射**：

| 虚拟路径 | 实际路径 |
|----------|----------|
| `/mnt/user-data/workspace` | `{base_dir}/threads/{thread_id}/user-data/workspace` |
| `/mnt/user-data/uploads` | `{base_dir}/threads/{thread_id}/user-data/uploads` |
| `/mnt/user-data/outputs` | `{base_dir}/threads/{thread_id}/user-data/outputs` |

### 4. Subagents 模块

**位置**: [subagents/](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/subagents/)

**内置子Agent**：

| 名称 | 用途 | 最大轮次 | 默认超时 |
|------|------|----------|----------|
| `general-purpose` | 复杂多步骤任务 | 50 | 900秒（15分钟） |
| `bash` | 命令执行专家 | 30 | 900秒（15分钟） |

**子Agent配置结构**：

```python
@dataclass
class SubagentConfig:
    name: str                           # 唯一标识
    description: str                    # 使用场景描述
    system_prompt: str                  # 系统提示词
    tools: list[str] | None = None      # 允许的工具列表
    disallowed_tools: list[str] | None  # 禁用的工具列表
    model: str = "inherit"              # 模型（"inherit" 继承父Agent）
    max_turns: int = 50                 # 最大轮次
    timeout_seconds: int = 900          # 超时时间（秒）
```

**执行流程**：

```
Task Tool 调用
    │
    ▼
SubagentExecutor.execute_async()
    │
    ▼
后台线程池执行
    │
    ▼
轮询检查状态
    │
    ▼
返回结果 / 超时 / 失败
```

### 5. Tools 模块

**位置**: [tools/](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/tools/)

**内置工具**：

| 工具名 | 功能 |
|--------|------|
| `setup_agent` | 创建自定义Agent |
| `ask_clarification` | 请求用户澄清 |
| `present_file` | 展示文件内容 |
| `view_image` | 查看图像（仅视觉模型） |
| `task` | 委托子Agent任务（仅 subagent_enabled 时可用） |

**工具加载流程**：

```python
def get_available_tools(
    groups: list[str] | None = None,
    include_mcp: bool = True,
    model_name: str | None = None,
    subagent_enabled: bool = False,
) -> list[BaseTool]:
    # 1. 从配置加载工具
    # 2. 加载 MCP 工具（缓存）
    # 3. 添加内置工具（setup_agent, ask_clarification, present_file）
    # 4. 条件添加 view_image（视觉模型）
    # 5. 条件添加 task（子Agent启用时）
```

### 6. Skills 模块

**位置**: [skills/](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/skills/)

**技能结构**：

```
skills/
├── public/           # 公共技能
│   └── {skill_name}/
│       └── SKILL.md
└── custom/           # 自定义技能
    └── {skill_name}/
        └── SKILL.md
```

**SKILL.md 格式**：

```markdown
---
name: skill-name
description: 技能描述
license: MIT
---

# 技能内容
...
```

### 7. MCP 模块

**位置**: [mcp/](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/mcp/)

**支持的传输类型**：
- `stdio`: 标准输入输出
- `sse`: Server-Sent Events
- `http`: HTTP 连接

**工具缓存**：

```python
# 启动时初始化
async def initialize_mcp_tools():
    tools = await get_mcp_tools()
    cache_mcp_tools(tools)
```

### 8. Models 模块

**位置**: [models/](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/models/)

**模型工厂**：

```python
def create_chat_model(
    name: str | None = None,
    thinking_enabled: bool = False,
    **kwargs
) -> BaseChatModel:
    # 1. 获取模型配置
    # 2. 解析模型类
    # 3. 应用 thinking 设置
    # 4. 附加追踪器
```

**特殊处理**：
- `PatchedChatDeepSeek`: 修复 DeepSeek 模型的 reasoning_content 保留问题

---

## 关键代码逻辑分析

### 1. Agent创建流程

```python
# agents/lead_agent/agent.py

def make_lead_agent(config: RunnableConfig):
    # 1. 解析配置参数
    thinking_enabled = cfg.get("thinking_enabled", True)
    model_name = cfg.get("model_name")
    is_plan_mode = cfg.get("is_plan_mode", False)
    subagent_enabled = cfg.get("subagent_enabled", False)
    
    # 2. 验证模型支持
    if thinking_enabled and not model_config.supports_thinking:
        logger.warning("Model does not support thinking")
        thinking_enabled = False
    
    # 3. 创建模型实例
    model = create_chat_model(
        name=model_name,
        thinking_enabled=thinking_enabled
    )
    
    # 4. 获取工具列表
    tools = get_available_tools(
        model_name=model_name,
        subagent_enabled=subagent_enabled
    )
    
    # 5. 构建中间件链
    middleware = _build_middlewares(config, model_name)
    
    # 6. 创建Agent
    return create_agent(
        model=model,
        tools=tools,
        middleware=middleware,
        system_prompt=apply_prompt_template(...),
        state_schema=ThreadState,
        checkpointer=checkpointer
    )
```

### 2. 中间件执行顺序

```
请求进入
    │
    ▼
before_agent (ThreadData, Sandbox, Uploads)
    │
    ▼
wrap_model_call (DanglingToolCall)
    │
    ▼
模型调用
    │
    ▼
after_model (Title, ViewImage)
    │
    ▼
wrap_tool_call (ToolErrorHandling, Clarification, LoopDetection)
    │
    ▼
after_agent (Sandbox release, Memory)
    │
    ▼
响应返回
```

### 3. 循环检测机制

```python
# agents/middlewares/loop_detection_middleware.py

class LoopDetectionMiddleware:
    def _track_and_check(self, state, runtime):
        # 1. 获取最近的工具调用
        tool_calls = last_msg.tool_calls
        
        # 2. 计算调用哈希
        call_hash = _hash_tool_calls(tool_calls)
        
        # 3. 更新历史记录
        self._history[thread_id].append(call_hash)
        
        # 4. 检测重复
        count = history.count(call_hash)
        
        # 5. 警告或强制停止
        if count >= self.warn_threshold:
            return WARNING_MSG, False
        if count >= self.hard_limit:
            return HARD_STOP_MSG, True
```

### 4. 子Agent执行机制

```python
# subagents/executor.py

class SubagentExecutor:
    def execute_async(self, prompt: str, task_id: str) -> str:
        # 1. 创建结果占位
        _background_tasks[task_id] = SubagentResult(
            task_id=task_id,
            status=SubagentStatus.PENDING
        )
        
        # 2. 提交到线程池
        future = _execution_pool.submit(
            self._run_sync,
            prompt,
            task_id
        )
        
        # 3. 设置超时回调
        future.add_done_callback(
            lambda f: self._handle_completion(task_id, f)
        )
        
        return task_id
```

### 5. 记忆更新流程

```python
# agents/memory/queue.py

class MemoryUpdateQueue:
    def add(self, thread_id, messages, agent_name):
        # 1. 添加到队列
        self._queue.append(context)
        
        # 2. 重置防抖计时器
        self._reset_timer()
    
    def _process_queue(self):
        # 1. 取出所有待处理项
        contexts = self._queue.copy()
        
        # 2. 逐个处理
        for context in contexts:
            updater.update_memory(
                messages=context.messages,
                thread_id=context.thread_id
            )
```

---

## 接口设计文档

### 1. DeerFlowClient API

**位置**: [client.py](file:///Users/lzc/TNTprojectZ/deer-flow/backend/packages/harness/deerflow/client.py)

#### 初始化

```python
client = DeerFlowClient(
    config_path: str | None = None,      # 配置文件路径
    checkpointer=None,                    # 状态持久化器
    model_name: str | None = None,        # 模型名称
    thinking_enabled: bool = True,        # 启用思考模式
    subagent_enabled: bool = False,       # 启用子Agent
    plan_mode: bool = False,              # 计划模式
)
```

#### 流式对话

```python
for event in client.stream(
    message: str,                         # 用户消息
    thread_id: str | None = None,         # 线程ID
    **kwargs                              # 其他参数
):
    # event.type: "values" | "messages-tuple" | "end"
    # event.data: 事件数据
```

#### 单次对话

```python
response: str = client.chat(
    message: str,
    thread_id: str | None = None,
    **kwargs
)
```

#### 配置查询

```python
# 返回模型列表（dict 格式，匹配 Gateway API 响应）
models: dict = client.list_models()
# 返回: {"models": [{"name": ..., "display_name": ..., ...}]}

# 返回技能列表
skills: dict = client.list_skills(enabled_only: bool = False)
# 返回: {"skills": [{"name": ..., "description": ..., ...}]}

# 获取记忆数据
memory: dict = client.get_memory()
```

### 2. 工具接口

#### setup_agent

```python
@tool
def setup_agent(
    soul: str,                            # SOUL.md 内容
    description: str,                     # Agent描述
    runtime: ToolRuntime,                 # 运行时上下文
) -> Command:
    """创建自定义 DeerFlow Agent"""
```

#### ask_clarification

```python
@tool("ask_clarification")
def ask_clarification_tool(
    question: str,                        # 澄清问题
    clarification_type: Literal[          # 澄清类型
        "missing_info",
        "ambiguous_requirement", 
        "approach_choice",
        "risk_confirmation",
        "suggestion"
    ],
    context: str | None = None,           # 上下文
    options: list[str] | None = None,     # 选项列表
) -> str:
```

#### task

```python
@tool("task")
def task_tool(
    description: str,                     # 任务描述
    prompt: str,                          # 详细提示
    subagent_type: Literal[               # 子Agent类型
        "general-purpose", 
        "bash"
    ],
    max_turns: int | None = None,         # 最大轮次
) -> str:
```

### 3. 沙箱接口

```python
class Sandbox(ABC):
    def execute_command(self, command: str) -> str:
        """执行命令"""
    
    def read_file(self, path: str) -> str:
        """读取文件"""
    
    def write_file(self, path: str, content: str, append: bool = False) -> None:
        """写入文件"""
    
    def list_dir(self, path: str, max_depth: int = 2) -> list[str]:
        """列出目录"""
    
    def update_file(self, path: str, content: bytes) -> None:
        """更新文件（二进制）"""
```

### 4. 配置接口

#### 模型配置

```python
class ModelConfig(BaseModel):
    name: str                              # 模型名称
    display_name: str | None               # 显示名称
    description: str | None                # 描述
    use: str                               # 类路径
    model: str                             # 模型标识
    supports_thinking: bool = False        # 支持思考
    supports_reasoning_effort: bool = False # 支持推理强度
    supports_vision: bool = False          # 支持视觉
    when_thinking_enabled: dict | None     # 思考模式配置
    thinking: dict | None                  # 思考设置快捷方式
```

#### Agent配置

```python
class AgentConfig(BaseModel):
    name: str                              # Agent名称
    description: str = ""                  # 描述
    model: str | None = None               # 使用的模型
    tool_groups: list[str] | None = None   # 工具组
```

---

## 数据流程说明

### 1. 请求处理流程

```
用户请求
    │
    ▼
┌─────────────────────────────────────┐
│         DeerFlowClient              │
│  1. 解析请求参数                      │
│  2. 获取/创建Agent实例                │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       ThreadDataMiddleware          │
│  创建线程数据目录                      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       SandboxMiddleware             │
│  创建/获取沙箱环境                     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       UploadsMiddleware             │
│  注入上传文件信息                      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│          Lead Agent                 │
│  1. 构建系统提示词                    │
│  2. 调用 LLM 模型                    │
│  3. 执行工具调用                      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       TitleMiddleware               │
│  生成对话标题                         │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       MemoryMiddleware              │
│  队列化记忆更新                       │
└─────────────────────────────────────┘
    │
    ▼
响应返回
```

### 2. 工具调用流程

```
LLM 返回工具调用
    │
    ▼
┌─────────────────────────────────────┐
│     ToolErrorHandlingMiddleware     │
│  捕获工具异常，转换为错误消息            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│     LoopDetectionMiddleware         │
│  检测重复调用                         │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│    ClarificationMiddleware          │
│  拦截澄清请求                         │
└─────────────────────────────────────┘
    │
    ▼ (普通工具)
┌─────────────────────────────────────┐
│          Tool Execution             │
│  执行工具逻辑                         │
└─────────────────────────────────────┘
    │
    ▼
返回工具结果
```

### 3. 子Agent执行流程

```
task 工具调用
    │
    ▼
┌─────────────────────────────────────┐
│        SubagentExecutor             │
│  1. 获取子Agent配置                   │
│  2. 过滤工具列表                      │
│  3. 创建子Agent实例                   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│      Background Thread Pool         │
│  异步执行子Agent                      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│          Polling Loop               │
│  轮询检查执行状态                      │
│  发送进度事件                         │
└─────────────────────────────────────┘
    │
    ▼
返回结果 / 超时 / 失败
```

### 4. 状态持久化流程

```
Agent执行完成
    │
    ▼
┌─────────────────────────────────────┐
│          Checkpointer               │
│  保存状态快照                         │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       Storage Backend               │
│  Memory / SQLite / PostgreSQL       │
└─────────────────────────────────────┘
    │
    下次请求时
    ▼
┌─────────────────────────────────────┐
│          Load State                 │
│  恢复对话历史                         │
└─────────────────────────────────────┘
```

---

## 开发规范

### 1. 代码风格

- **类型注解**：所有函数必须有类型注解
- **文档字符串**：公共 API 必须有 docstring
- **导入顺序**：标准库 → 第三方库 → 本地模块

### 2. 模块设计原则

#### 中间件开发

```python
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

class CustomMiddleware(AgentMiddleware[CustomState]):
    state_schema = CustomState
    
    def before_agent(self, state, runtime: Runtime) -> dict | None:
        """Agent执行前"""
        return {"key": "value"}  # 返回状态更新
    
    async def aafter_model(self, state, runtime: Runtime) -> dict | None:
        """模型响应后（异步）"""
        return None
    
    def wrap_tool_call(self, request, handler):
        """包装工具调用"""
        return handler(request)
```

#### 工具开发

```python
from langchain.tools import tool, ToolRuntime

@tool("tool_name", parse_docstring=True)
def my_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    param1: str,
    param2: int = 10,
) -> str:
    """工具描述
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
    """
    # 访问状态
    thread_data = runtime.state.get("thread_data")
    # 访问上下文
    thread_id = runtime.context.get("thread_id")
    
    return "result"
```

### 3. 配置扩展

#### 添加新模型

```yaml
# config.yaml
models:
  - name: my-model
    display_name: My Model
    description: Custom model
    use: langchain_openai:ChatOpenAI
    model: gpt-4
    supports_thinking: false
    supports_vision: true
```

#### 添加自定义Agent

```yaml
# agents/my-agent/config.yaml
name: my-agent
description: My custom agent
model: my-model
tool_groups:
  - default
```

```markdown
# agents/my-agent/SOUL.md
# My Agent Personality

You are a specialized agent for...
```

### 4. 错误处理

```python
from deerflow.sandbox.exceptions import (
    SandboxError,
    SandboxNotFoundError,
    SandboxRuntimeError,
)

try:
    result = sandbox.execute_command(command)
except SandboxNotFoundError as e:
    # 沙箱不存在
except SandboxRuntimeError as e:
    # 执行错误
except SandboxError as e:
    # 通用沙箱错误
```

### 5. 日志规范

```python
import logging

logger = logging.getLogger(__name__)

# 使用结构化日志
logger.info(
    "Agent created: model=%s, thinking=%s",
    model_name,
    thinking_enabled
)

# 错误日志包含上下文
logger.error(
    "Failed to execute command: %s",
    command,
    exc_info=True
)
```

### 6. 测试规范

```python
import pytest
from deerflow.client import DeerFlowClient

@pytest.fixture
def client():
    return DeerFlowClient(checkpointer=InMemorySaver())

def test_chat(client):
    response = client.chat("Hello")
    assert response is not None
```

---

## 附录

### A. 环境变量

| 变量名 | 说明 |
|--------|------|
| `DEER_FLOW_CONFIG_PATH` | 配置文件路径 |
| `DEER_FLOW_HOME` | 数据目录 |
| `DEER_FLOW_HOST_BASE_DIR` | Docker 主机路径 |

### B. 依赖包

| 包名 | 用途 |
|------|------|
| `langchain` | Agent框架 |
| `langgraph` | 状态图 |
| `langchain-mcp-adapters` | MCP 协议 |
| `langgraph-checkpoint-sqlite` | SQLite 持久化 |
| `langgraph-checkpoint-postgres` | PostgreSQL 持久化 |

### C. 参考链接

- [LangChain 文档](https://python.langchain.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [MCP 协议](https://modelcontextprotocol.io/)
