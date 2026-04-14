# 计划模式（Plan Mode）与 TodoList 中间件

本文档描述如何在 DeerFlow 2.0 中启用和使用带有 TodoList 中间件的计划模式（Plan Mode）功能。

## 概述

计划模式（Plan Mode）为智能体（agent）添加了一个 TodoList 中间件，该中间件提供了一个 `write_todos` 工具，帮助智能体：
- 将复杂任务分解为更小、可管理的步骤
- 跟踪工作进展情况
- 向用户提供正在执行的任务的可见性

TodoList 中间件基于 LangChain 的 `TodoListMiddleware` 构建。

## 配置

### 启用计划模式

计划模式通过 `RunnableConfig` 的 `configurable` 部分中的 `is_plan_mode` 参数进行**运行时配置**控制。这允许您在每个请求的基础上动态启用或禁用计划模式。

```python
from langchain_core.runnables import RunnableConfig
from deerflow.agents.lead_agent.agent import make_lead_agent

# 通过运行时配置启用计划模式
config = RunnableConfig(
    configurable={
        "thread_id": "example-thread",
        "thinking_enabled": True,
        "is_plan_mode": True,  # 启用计划模式
    }
)

# 创建启用了计划模式的智能体
agent = make_lead_agent(config)
```

### 配置选项

- **is_plan_mode** (布尔值): 是否启用带有 TodoList 中间件的计划模式。默认值: `False`
  - 通过 `config.get("configurable", {}).get("is_plan_mode", False)` 传递
  - 可以为每次智能体调用动态设置
  - 不需要全局配置

## 默认行为

当计划模式在默认设置下启用时，智能体将可以使用具有以下行为的 `write_todos` 工具：

### 何时使用 TodoList

智能体将在以下情况使用待办事项列表：
1. 复杂的多步骤任务（3个或更多不同步骤）
2. 需要仔细规划的非 trivial 任务
3. 当用户明确要求待办事项列表时
4. 当用户提供多个任务时

### 何时不使用 TodoList

智能体将在以下情况跳过使用待办事项列表：
1. 单一、直接的任务
2. 简单任务（少于3个步骤）
3. 纯粹的对话或信息请求

### 任务状态

- **pending**（待处理）: 任务尚未开始
- **in_progress**（进行中）: 当前正在处理（可以有多个并行任务）
- **completed**（已完成）: 任务成功完成

## 使用示例

### 基本用法

```python
from langchain_core.runnables import RunnableConfig
from deerflow.agents.lead_agent.agent import make_lead_agent

# 创建启用了计划模式的智能体
config_with_plan_mode = RunnableConfig(
    configurable={
        "thread_id": "example-thread",
        "thinking_enabled": True,
        "is_plan_mode": True,  # 将添加 TodoList 中间件
    }
)
agent_with_todos = make_lead_agent(config_with_plan_mode)

# 创建禁用了计划模式的智能体（默认）
config_without_plan_mode = RunnableConfig(
    configurable={
        "thread_id": "another-thread",
        "thinking_enabled": True,
        "is_plan_mode": False,  # 无 TodoList 中间件
    }
)
agent_without_todos = make_lead_agent(config_without_plan_mode)
```

### 每个请求动态启用计划模式

您可以为不同的对话或任务动态启用/禁用计划模式：

```python
from langchain_core.runnables import RunnableConfig
from deerflow.agents.lead_agent.agent import make_lead_agent

def create_agent_for_task(task_complexity: str):
    """根据任务复杂度创建带有计划模式的智能体。"""
    is_complex = task_complexity in ["high", "very_high"]

    config = RunnableConfig(
        configurable={
            "thread_id": f"task-{task_complexity}",
            "thinking_enabled": True,
            "is_plan_mode": is_complex,  # 仅对复杂任务启用
        }
    )

    return make_lead_agent(config)

# 简单任务 - 不需要 TodoList
simple_agent = create_agent_for_task("low")

# 复杂任务 - 启用 TodoList 以更好地跟踪
complex_agent = create_agent_for_task("high")
```

## 工作原理

1. 当调用 `make_lead_agent(config)` 时，它从 `config.configurable` 中提取 `is_plan_mode`
2. 配置被传递给 `_build_middlewares(config)`
3. `_build_middlewares()` 读取 `is_plan_mode` 并调用 `_create_todo_list_middleware(is_plan_mode)`
4. 如果 `is_plan_mode=True`，则创建 `TodoListMiddleware` 实例并将其添加到中间件链中
5. 中间件自动向智能体的工具集添加 `write_todos` 工具
6. 智能体可以在执行过程中使用此工具管理任务
7. 中间件处理待办事项列表状态并将其提供给智能体

## 架构

```
make_lead_agent(config)
  │
  ├─> 提取: is_plan_mode = config.configurable.get("is_plan_mode", False)
  │
  └─> _build_middlewares(config)
        │
        ├─> ThreadDataMiddleware
        ├─> SandboxMiddleware
        ├─> SummarizationMiddleware (如果通过全局配置启用)
        ├─> TodoListMiddleware (如果 is_plan_mode=True) ← 新增
        ├─> TitleMiddleware
        └─> ClarificationMiddleware
```

## 实现细节

### 智能体模块
- **位置**: `packages/harness/deerflow/agents/lead_agent/agent.py`
- **函数**: `_create_todo_list_middleware(is_plan_mode: bool)` - 如果启用计划模式，则创建 TodoListMiddleware
- **函数**: `_build_middlewares(config: RunnableConfig)` - 根据运行时配置构建中间件链
- **函数**: `make_lead_agent(config: RunnableConfig)` - 创建具有适当中间件的智能体

### 运行时配置
计划模式通过 `RunnableConfig.configurable` 中的 `is_plan_mode` 参数控制：
```python
config = RunnableConfig(
    configurable={
        "is_plan_mode": True,  # 启用计划模式
        # ... 其他可配置选项
    }
)
```

## 主要优势

1. **动态控制**：无需全局状态，每个请求都可以启用/禁用计划模式
2. **灵活性**：不同的对话可以有不同的计划模式设置
3. **简洁性**：无需全局配置管理
4. **上下文感知**：计划模式决策可以基于任务复杂度、用户偏好等

## 自定义提示

DeerFlow 为 TodoListMiddleware 使用自定义的 `system_prompt` 和 `tool_description`，以匹配整体 DeerFlow 提示风格：

### 系统提示特性
- 使用 XML 标签 (`<todo_list_system>`) 与 DeerFlow 的主提示保持结构一致性
- 强调关键规则和最佳实践
- 明确的"何时使用"与"何时不使用"指南
- 专注于实时更新和即时任务完成

### 工具描述特性
- 详细的使用场景和示例
- 强调不要用于简单任务
- 清晰的任务状态定义（pending、in_progress、completed）
- 全面的最佳实践部分
- 任务完成要求，防止过早标记

自定义提示定义在 `_create_todo_list_middleware()` 中，位于 `/Users/hetao/workspace/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py:57`。

## 注意事项

- TodoList 中间件使用 LangChain 的内置 `TodoListMiddleware` 与**自定义 DeerFlow 风格提示**
- 计划模式默认**禁用** (`is_plan_mode=False`)，以保持向后兼容性
- 中间件位于 `ClarificationMiddleware` 之前，以允许在澄清流程中管理待办事项
- 自定义提示强调与 DeerFlow 主系统提示相同的原则（清晰、行动导向、关键规则）