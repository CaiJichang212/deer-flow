"""Filter illegal tool calls during pending-review stage in plan mode."""

from __future__ import annotations

import logging
from typing import Any, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)

_ALLOWED_TOOLS_PENDING_REVIEW = {"write_todos", "review_plan", "ask_clarification"}


class PlanToolWhitelistMiddleware(AgentMiddleware[AgentState]):
    """Drop non-whitelisted tool calls when plan_review is pending_review."""

    def _apply(self, state: AgentState, runtime: Runtime) -> dict | None:
        plan_review = state.get("plan_review")
        if not isinstance(plan_review, dict):
            return None
        if plan_review.get("status") != "pending_review":
            return None

        messages = state.get("messages", [])
        if not messages:
            return None
        last_msg = messages[-1]
        if not isinstance(last_msg, AIMessage):
            return None

        tool_calls = getattr(last_msg, "tool_calls", None)
        if not isinstance(tool_calls, list) or len(tool_calls) == 0:
            return None

        kept = []
        removed_names: list[str] = []
        for call in tool_calls:
            name = str(call.get("name") or "")
            if name in _ALLOWED_TOOLS_PENDING_REVIEW:
                kept.append(call)
            else:
                removed_names.append(name or "unknown")

        if len(removed_names) == 0:
            return None

        logger.info(
            "metric=plan_guard_block_count code=PLAN_TOOL_FILTERED removed=%s thread_id=%s",
            ",".join(removed_names),
            runtime.context.get("thread_id") if runtime.context else None,
        )
        updated_msg = last_msg.model_copy(update={"tool_calls": kept})
        reminder = HumanMessage(
            name="plan_tool_filtered",
            content=(
                "<system_reminder>\n"
                f"待审核阶段仅允许调用 {sorted(_ALLOWED_TOOLS_PENDING_REVIEW)}。"
                f"已过滤工具：{', '.join(removed_names)}。\n"
                "请先完善计划并调用 `review_plan`。\n"
                "</system_reminder>"
            ),
        )
        return {"messages": [updated_msg, reminder]}

    @override
    def after_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._apply(state, runtime)

    @override
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._apply(state, runtime)

