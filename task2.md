一、参考DeerFlow编写后端API文档 v1版
1. 提供两组API：智能体API负责Agent交互、线程管理和流式响应，Gateway API负责模型管理和MCP配置。
2. 智能体API支持创建线程、获取状态、执行运行等操作，支持实时流式响应。
3. Gateway API提供模型列表查询、模型详情获取以及MCP服务器配置的读取和更新功能。

二、整理借鉴DeerFlow的技术方案
1. 使用 LangGraph 的 Checkpointer 实现状态持久化，支持2种后端：memory 进程内存，重启丢失；sqlite 文件持久化，单进程。
2. ToolErrorHandlingMiddleware（工具错误处理），捕获工具执行异常，转换为错误 ToolMessage，记录详细日志（工具名称、调用ID、异常详情），允许 Agent 继续运行而非崩溃。
3. MCP集成，通过extensions_config.json文件，配置MCP工具，支持自定义，新增。

三、修改、完善sh项目的420节点的需求文档 v1版
1. 基础功能：聊天Session管理，包括创建、切换、删除Session等；多轮对话支持。
2. Agent自主判断：明确区分简单任务和复杂任务的处理路径，Agent自主判断是否需要调用工具。
对于简单任务，Agent直接生成回答；
对于复杂任务，Agent自动进入计划-确认-执行流程。
3. 用户确认机制：使用LangGraph的interrupt机制实现计划确认。
4. 使用langfuse库记录Agent执行过程，包括用户输入、模型输出、工具调用结果、报错信息等。

