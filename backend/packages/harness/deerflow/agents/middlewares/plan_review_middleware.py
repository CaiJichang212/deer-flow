"""Middleware for plan-review interrupt and resume gating in Pro mode."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, NotRequired, TypedDict, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import END
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

logger = logging.getLogger(__name__)

_PLAN_REVIEW_TOOL_NAME = "review_plan"
_MISSING_TOOL_CALL_ID = "missing_tool_call_id"
_PLAN_ACTION_CONFIRM = "confirm"
_PLAN_ACTION_RETRY = "retry"
_PENDING_REVIEW = "pending_review"
_EXECUTING = "executing"


class PlanReviewTodo(TypedDict):
    content: str
    status: NotRequired[str]


class PlanReviewState(TypedDict):
    status: str
    version: int
    todos: list[PlanReviewTodo]
    updated_at: int
    title: NotRequired[str]


class PlanReviewMiddlewareState(AgentState):
    """Compatible with ThreadState schema."""

    plan_review: NotRequired[PlanReviewState | None]


def _parse_json_string(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


def _normalize_todos(raw_todos: Any) -> list[PlanReviewTodo]:
    raw_todos = _parse_json_string(raw_todos)
    if not isinstance(raw_todos, list):
        return []

    todos: list[PlanReviewTodo] = []
    for item in raw_todos:
        if isinstance(item, str):
            content = item.strip()
            if content:
                todos.append({"content": content})
            continue

        item = _parse_json_string(item)
        if not isinstance(item, dict):
            continue

        content = str(item.get("content", "")).strip()
        if not content:
            continue

        todo: PlanReviewTodo = {"content": content}
        status = item.get("status")
        if status is not None:
            todo["status"] = str(status)
        todos.append(todo)

    return todos


def _extract_last_plan_action(messages: list[Any]) -> tuple[str | None, int | None]:
    for message in reversed(messages):
        if getattr(message, "type", None) != "human":
            continue
        kwargs = getattr(message, "additional_kwargs", {}) or {}
        action = kwargs.get("plan_action")
        if action in (_PLAN_ACTION_CONFIRM, _PLAN_ACTION_RETRY):
            raw_version = kwargs.get("plan_version")
            try:
                parsed_version = int(raw_version) if raw_version is not None else None
            except (TypeError, ValueError):
                parsed_version = None
            return str(action), parsed_version
    return None, None


def _extract_latest_human_kwargs(messages: list[Any]) -> dict[str, Any]:
    for message in reversed(messages):
        if getattr(message, "type", None) != "human":
            continue
        kwargs = getattr(message, "additional_kwargs", {}) or {}
        if isinstance(kwargs, dict):
            return kwargs
        return {}
    return {}


def _is_pending_review(plan_review: Any) -> bool:
    return isinstance(plan_review, dict) and plan_review.get("status") == _PENDING_REVIEW


class PlanReviewMiddleware(AgentMiddleware[PlanReviewMiddlewareState]):
    """Intercepts review_plan calls and gates execution until user confirmation."""

    state_schema = PlanReviewMiddlewareState

    _ALLOWED_TOOLS_DURING_REVIEW = {
        "ask_clarification",
        "write_todos",
        _PLAN_REVIEW_TOOL_NAME,
    }

    def _build_invalid_plan_error(self, request: ToolCallRequest) -> Command:
        tool_call_id = str(request.tool_call.get("id") or _MISSING_TOOL_CALL_ID)
        tool_message = ToolMessage(
            content="计划无效：`todos` 至少需要 1 条非空任务，请重新生成计划后再次提交审核。",
            tool_call_id=tool_call_id,
            name=_PLAN_REVIEW_TOOL_NAME,
            status="error",
        )
        return Command(
            update={"messages": [tool_message]},
            goto=END,
        )

    def _handle_review_plan(self, request: ToolCallRequest) -> Command:
        args = request.tool_call.get("args", {})
        args = _parse_json_string(args)
        if not isinstance(args, dict):
            args = {}

        todos = _normalize_todos(args.get("todos"))
        if len(todos) == 0:
            logger.warning("Invalid review_plan payload: empty todos")
            return self._build_invalid_plan_error(request)

        prior = request.state.get("plan_review")
        prior_version = prior.get("version", 0) if isinstance(prior, dict) else 0
        version = int(prior_version) + 1
        updated_at = int(time.time())

        plan_review: PlanReviewState = {
            "status": _PENDING_REVIEW,
            "version": version,
            "todos": todos,
            "updated_at": updated_at,
        }
        title = args.get("title")
        if isinstance(title, str) and title.strip():
            plan_review["title"] = title.strip()

        summary_lines = [f"计划已生成，等待审核（v{version}）。"]
        for idx, todo in enumerate(todos, start=1):
            summary_lines.append(f"{idx}. {todo['content']}")

        tool_call_id = str(request.tool_call.get("id") or _MISSING_TOOL_CALL_ID)
        tool_message = ToolMessage(
            content="\n".join(summary_lines),
            tool_call_id=tool_call_id,
            name=_PLAN_REVIEW_TOOL_NAME,
        )

        logger.info("Plan review pending: version=%s todos=%s", version, len(todos))
        return Command(
            update={
                "messages": [tool_message],
                "plan_review": plan_review,
                "todos": todos,
            },
            goto=END,
        )

    def _build_version_mismatch_command(self, request: ToolCallRequest, expected: int, got: int | None) -> Command:
        tool_call_id = str(request.tool_call.get("id") or _MISSING_TOOL_CALL_ID)
        message = ToolMessage(
            content=(
                f"计划版本不匹配：当前版本为 v{expected}，收到确认版本为 "
                f"{'空' if got is None else f'v{got}'}。请刷新后重新确认。"
            ),
            tool_call_id=tool_call_id,
            name=str(request.tool_call.get("name") or "unknown_tool"),
            status="error",
        )
        return Command(update={"messages": [message]}, goto=END)

    def _build_pending_review_block_command(self, request: ToolCallRequest) -> Command:
        tool_call_id = str(request.tool_call.get("id") or _MISSING_TOOL_CALL_ID)
        tool_name = str(request.tool_call.get("name") or "unknown_tool")
        message = ToolMessage(
            content="计划仍处于待审核状态，请先点击“确认”或“重试生成计划”。",
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )
        return Command(update={"messages": [message]}, goto=END)

    def _build_missing_review_block_command(self, request: ToolCallRequest) -> Command:
        tool_call_id = str(request.tool_call.get("id") or _MISSING_TOOL_CALL_ID)
        tool_name = str(request.tool_call.get("name") or "unknown_tool")
        message = ToolMessage(
            content="Pro 模式要求先生成计划并调用 `review_plan` 完成审核，再执行具体任务。",
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )
        return Command(update={"messages": [message]}, goto=END)

    @override
    def before_model(self, state: PlanReviewMiddlewareState, runtime) -> dict[str, Any] | None:
        if not runtime.context.get("is_plan_mode", False):
            return None

        plan_review = state.get("plan_review")
        if not _is_pending_review(plan_review):
            return None

        messages = state.get("messages", []) or []
        action, action_version = _extract_last_plan_action(messages)
        current_version = int(plan_review.get("version", 0)) if isinstance(plan_review, dict) else 0

        if action == _PLAN_ACTION_CONFIRM and (action_version is None or action_version == current_version):
            updated_review = {
                **plan_review,
                "status": _EXECUTING,
                "updated_at": int(time.time()),
            }
            todos = updated_review.get("todos", [])
            todo_lines = "\n".join(f"- {todo.get('content', '')}" for todo in todos)
            reminder = HumanMessage(
                name="plan_review_confirmed",
                content=(
                    "<system_reminder>\n"
                    f"用户已确认计划（v{current_version}）。请按以下计划执行：\n\n"
                    f"{todo_lines}\n\n"
                    "现在可以开始执行具体步骤。\n"
                    "</system_reminder>"
                ),
            )
            return {
                "plan_review": updated_review,
                "todos": todos,
                "messages": [reminder],
            }

        if action == _PLAN_ACTION_RETRY:
            reminder = HumanMessage(
                name="plan_review_retry",
                content=(
                    "<system_reminder>\n"
                    "用户要求重试计划。请先重新整理 todo 计划，再调用 `review_plan` 进入下一轮审核。"
                    "在新的计划获批前，不要执行计划任务。\n"
                    "</system_reminder>"
                ),
            )
            return {"messages": [reminder]}

        return None

    def _maybe_gate_tool_call(self, request: ToolCallRequest) -> Command | None:
        if request.tool_call.get("name") == _PLAN_REVIEW_TOOL_NAME:
            return None

        tool_name = str(request.tool_call.get("name") or "")
        messages = request.state.get("messages", []) or []
        action, action_version = _extract_last_plan_action(messages)
        latest_human_kwargs = _extract_latest_human_kwargs(messages)

        if action is None and latest_human_kwargs.get("plan_action") is None and tool_name not in self._ALLOWED_TOOLS_DURING_REVIEW:
            return self._build_missing_review_block_command(request)

        plan_review = request.state.get("plan_review")
        if not _is_pending_review(plan_review):
            return None

        current_version = int(plan_review.get("version", 0)) if isinstance(plan_review, dict) else 0

        if action == _PLAN_ACTION_CONFIRM:
            if action_version is not None and action_version != current_version:
                return self._build_version_mismatch_command(request, expected=current_version, got=action_version)
            return None

        if action == _PLAN_ACTION_RETRY:
            if tool_name in self._ALLOWED_TOOLS_DURING_REVIEW:
                return None
            return self._build_pending_review_block_command(request)

        if tool_name in self._ALLOWED_TOOLS_DURING_REVIEW:
            return None
        return self._build_pending_review_block_command(request)

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        tool_name = request.tool_call.get("name")
        if tool_name == _PLAN_REVIEW_TOOL_NAME:
            return self._handle_review_plan(request)

        gate_result = self._maybe_gate_tool_call(request)
        if gate_result is not None:
            return gate_result

        return handler(request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        tool_name = request.tool_call.get("name")
        if tool_name == _PLAN_REVIEW_TOOL_NAME:
            return self._handle_review_plan(request)

        gate_result = self._maybe_gate_tool_call(request)
        if gate_result is not None:
            return gate_result

        return await handler(request)
