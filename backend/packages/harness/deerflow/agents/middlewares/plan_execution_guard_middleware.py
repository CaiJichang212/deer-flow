"""Guard middleware to fail plan execution on repeated LLM failures."""

from __future__ import annotations

import logging
import time
from typing import Any, NotRequired, TypedDict, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)

_FAILED = "failed"
_APPROVED = "approved"
_EXECUTING = "executing"
_FAIL_PATTERNS = ("LLM request failed", "invalid_parameter_error")


class PlanExecutionGuardState(AgentState):
    plan_review: NotRequired[dict[str, Any] | None]


class PlanExecutionGuardMiddleware(AgentMiddleware[PlanExecutionGuardState]):
    """Detect repeated model failures and move plan_review to failed state."""

    def __init__(self, max_consecutive_failures: int = 2):
        super().__init__()
        self.max_consecutive_failures = max_consecutive_failures

    def _count_consecutive_failures(self, messages: list[Any]) -> int:
        count = 0
        for msg in reversed(messages):
            if not isinstance(msg, AIMessage):
                continue
            content = str(getattr(msg, "content", "") or "")
            if any(pattern in content for pattern in _FAIL_PATTERNS):
                count += 1
                continue
            break
        return count

    def _emit_event(self, runtime: Runtime, payload: dict[str, Any]) -> None:
        try:
            from langgraph.config import get_stream_writer

            writer = get_stream_writer()
            writer(payload)
        except Exception:
            logger.debug("Failed to emit plan guard event", exc_info=True)

    def _apply(self, state: PlanExecutionGuardState, runtime: Runtime) -> dict | None:
        plan_review = state.get("plan_review")
        if not isinstance(plan_review, dict):
            return None

        status = str(plan_review.get("status", ""))
        if status not in {_APPROVED, _EXECUTING}:
            return None

        messages = state.get("messages", [])
        if not isinstance(messages, list) or len(messages) == 0:
            return None

        failures = self._count_consecutive_failures(messages)
        if failures < self.max_consecutive_failures:
            return None

        next_failures = int(plan_review.get("consecutive_failures", 0)) + 1
        now = int(time.time())
        updated_plan = {
            **plan_review,
            "status": _FAILED,
            "consecutive_failures": next_failures,
            "error_code": "PLAN_EXECUTION_FAILED",
            "error_message": "执行阶段发生连续模型失败，请重试计划。",
            "updated_at": now,
            "last_event_at": now,
        }

        self._emit_event(
            runtime,
            {
                "type": "plan_guard_blocked",
                "reason": "consecutive_llm_failures",
                "thread_id": runtime.context.get("thread_id") if runtime.context else None,
                "count": failures,
            },
        )
        logger.info(
            "metric=plan_failed_count reason=consecutive_llm_failures failures=%s thread_id=%s",
            failures,
            runtime.context.get("thread_id") if runtime.context else None,
        )
        reminder = HumanMessage(
            name="plan_execution_failed",
            content=(
                "<system_reminder>\n"
                "计划执行失败：检测到连续模型错误。请点击“重试”生成新计划后继续。\n"
                "</system_reminder>"
            ),
        )
        return {"plan_review": updated_plan, "messages": [reminder]}

    @override
    def after_model(self, state: PlanExecutionGuardState, runtime: Runtime) -> dict | None:
        return self._apply(state, runtime)

    @override
    async def aafter_model(
        self,
        state: PlanExecutionGuardState,
        runtime: Runtime,
    ) -> dict | None:
        return self._apply(state, runtime)

