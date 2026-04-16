"""Middleware to sanitize malformed tool call arguments before tool execution."""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from typing import Any, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)


def _coerce_jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _sanitize_args(raw_args: Any) -> tuple[dict[str, Any] | None, bool]:
    """Return (normalized_args, repaired). normalized_args=None means drop call."""
    if isinstance(raw_args, dict):
        try:
            normalized = _coerce_jsonable(raw_args)
        except Exception:
            return None, False
        return normalized if isinstance(normalized, dict) else None, normalized != raw_args

    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
        except Exception:
            return None, False
        if not isinstance(parsed, dict):
            return None, False
        return parsed, True

    return None, False


class ToolArgsSanitizationMiddleware(AgentMiddleware[AgentState]):
    """Sanitize invalid tool_call.args and remove unrecoverable malformed tool calls."""

    def _copy_message_with_tool_calls(self, message: Any, tool_calls: list[dict[str, Any]]) -> Any:
        if hasattr(message, "model_copy"):
            return message.model_copy(update={"tool_calls": tool_calls})
        data = dict(getattr(message, "__dict__", {}))
        data["tool_calls"] = tool_calls
        return SimpleNamespace(**data)

    def _apply(self, state: AgentState, runtime: Runtime) -> dict | None:
        messages = state.get("messages", [])
        if not messages:
            return None

        last_msg = messages[-1]
        if getattr(last_msg, "type", None) != "ai":
            return None

        tool_calls = getattr(last_msg, "tool_calls", None)
        if not isinstance(tool_calls, list) or len(tool_calls) == 0:
            return None

        sanitized_calls: list[dict[str, Any]] = []
        repaired_count = 0
        dropped: list[str] = []

        for tc in tool_calls:
            if not isinstance(tc, dict):
                dropped.append("unknown")
                continue
            tc_copy = dict(tc)
            normalized_args, repaired = _sanitize_args(tc_copy.get("args"))
            tool_name = str(tc_copy.get("name") or "unknown")
            if normalized_args is None:
                dropped.append(tool_name)
                continue
            if repaired:
                repaired_count += 1
            tc_copy["args"] = normalized_args
            sanitized_calls.append(tc_copy)

        if repaired_count == 0 and len(dropped) == 0:
            return None

        updated_msg = self._copy_message_with_tool_calls(last_msg, sanitized_calls)
        notice = HumanMessage(
            name="tool_args_repaired",
            content=(
                "<system_reminder>\n"
                "部分工具调用参数已自动修复或剔除，请继续使用合法 JSON 参数重发必要工具调用。\n"
                "</system_reminder>"
            ),
        )
        logger.info(
            "metric=tool_args_repair_count repaired=%s dropped=%s thread_id=%s",
            repaired_count,
            len(dropped),
            runtime.context.get("thread_id") if runtime.context else None,
        )
        return {"messages": [updated_msg, notice]}

    @override
    def after_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._apply(state, runtime)

    @override
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._apply(state, runtime)
