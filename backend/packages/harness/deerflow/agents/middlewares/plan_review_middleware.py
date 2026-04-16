"""Middleware for plan-review interrupt and strong execution gating in Pro mode."""

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

_PLAN_STATUS_PENDING = "pending_review"
_PLAN_STATUS_APPROVED = "approved"
_PLAN_STATUS_EXECUTING = "executing"
_PLAN_STATUS_COMPLETED = "completed"
_PLAN_STATUS_FAILED = "failed"

_PLAN_EVENT_SUBMIT = "submit_plan"
_PLAN_EVENT_CONFIRM = "confirm"
_PLAN_EVENT_RETRY = "retry"
_PLAN_EVENT_EXECUTION_STARTED = "execution_started"
_PLAN_EVENT_EXECUTION_COMPLETED = "execution_completed"
_PLAN_EVENT_EXECUTION_FAILED = "execution_failed"

_MAX_TODOS = 50


class PlanReviewTodo(TypedDict):
    content: str
    status: NotRequired[str]


class PlanReviewState(TypedDict):
    status: str
    version: int
    todos: list[PlanReviewTodo]
    updated_at: int
    title: NotRequired[str]
    error_code: NotRequired[str]
    error_message: NotRequired[str]
    consecutive_failures: NotRequired[int]
    last_event_at: NotRequired[int]


class PlanReviewMiddlewareState(AgentState):
    """Compatible with ThreadState schema."""

    plan_review: NotRequired[PlanReviewState | None]


_PLANNING_TOOLS = {
    "ask_clarification",
    "write_todos",
    _PLAN_REVIEW_TOOL_NAME,
}


def _parse_json_string(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


def _now_ts() -> int:
    return int(time.time())


def _normalize_todos(raw_todos: Any, *, max_items: int = _MAX_TODOS) -> list[PlanReviewTodo]:
    raw_todos = _parse_json_string(raw_todos)
    if not isinstance(raw_todos, list):
        return []

    todos: list[PlanReviewTodo] = []
    for item in raw_todos:
        if len(todos) >= max_items:
            break

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


def _extract_latest_human_kwargs(messages: list[Any]) -> dict[str, Any]:
    for message in reversed(messages):
        if getattr(message, "type", None) != "human":
            continue
        kwargs = getattr(message, "additional_kwargs", {}) or {}
        if isinstance(kwargs, dict):
            return kwargs
        return {}
    return {}


def _normalize_plan_action(messages: list[Any]) -> tuple[str | None, int | None]:
    kwargs = _extract_latest_human_kwargs(messages)
    action = kwargs.get("plan_action")
    if action not in {_PLAN_ACTION_CONFIRM, _PLAN_ACTION_RETRY}:
        return None, None

    raw_version = kwargs.get("plan_version")
    try:
        version = int(raw_version) if raw_version is not None else None
    except (TypeError, ValueError):
        version = None
    return str(action), version


def _all_todos_completed(state: PlanReviewMiddlewareState) -> bool:
    todos = state.get("todos")
    if not isinstance(todos, list) or len(todos) == 0:
        plan_review = state.get("plan_review")
        if isinstance(plan_review, dict):
            todos = plan_review.get("todos", [])
        else:
            return False
    if not isinstance(todos, list) or len(todos) == 0:
        return False
    for todo in todos:
        if not isinstance(todo, dict):
            return False
        if str(todo.get("status", "")).strip() != "completed":
            return False
    return True


def _transition(current_status: str | None, event: str) -> str:
    if event == _PLAN_EVENT_SUBMIT:
        return _PLAN_STATUS_PENDING
    if event == _PLAN_EVENT_RETRY:
        return _PLAN_STATUS_PENDING
    if event == _PLAN_EVENT_CONFIRM:
        return _PLAN_STATUS_APPROVED
    if event == _PLAN_EVENT_EXECUTION_STARTED:
        return _PLAN_STATUS_EXECUTING
    if event == _PLAN_EVENT_EXECUTION_COMPLETED:
        return _PLAN_STATUS_COMPLETED
    if event == _PLAN_EVENT_EXECUTION_FAILED:
        return _PLAN_STATUS_FAILED
    raise ValueError(f"Unsupported plan event: {event}")


def _validate_transition(current_status: str | None, event: str) -> None:
    transitions = {
        None: {_PLAN_EVENT_SUBMIT},
        _PLAN_STATUS_PENDING: {_PLAN_EVENT_SUBMIT, _PLAN_EVENT_CONFIRM, _PLAN_EVENT_RETRY},
        _PLAN_STATUS_APPROVED: {
            _PLAN_EVENT_SUBMIT,
            _PLAN_EVENT_RETRY,
            _PLAN_EVENT_EXECUTION_STARTED,
            _PLAN_EVENT_EXECUTION_COMPLETED,
            _PLAN_EVENT_EXECUTION_FAILED,
        },
        _PLAN_STATUS_EXECUTING: {
            _PLAN_EVENT_SUBMIT,
            _PLAN_EVENT_RETRY,
            _PLAN_EVENT_EXECUTION_COMPLETED,
            _PLAN_EVENT_EXECUTION_FAILED,
        },
        _PLAN_STATUS_COMPLETED: {_PLAN_EVENT_SUBMIT, _PLAN_EVENT_RETRY},
        _PLAN_STATUS_FAILED: {_PLAN_EVENT_SUBMIT, _PLAN_EVENT_RETRY},
    }
    allowed = transitions.get(current_status, set())
    if event not in allowed:
        raise ValueError(
            f"Invalid plan state transition: status={current_status!r}, event={event!r}",
        )


def _is_execution_tool(tool_name: str) -> bool:
    return tool_name not in _PLANNING_TOOLS


def _merge_command_update(command: Command, update: dict[str, Any]) -> Command:
    existing = dict(command.update or {})
    existing_messages = []
    if isinstance(existing.get("messages"), list):
        existing_messages = list(existing["messages"])
    new_messages = []
    if isinstance(update.get("messages"), list):
        new_messages = list(update["messages"])
    if existing_messages or new_messages:
        existing["messages"] = existing_messages + new_messages

    for key, value in update.items():
        if key == "messages":
            continue
        existing[key] = value
    return command.model_copy(update={"update": existing})


class PlanReviewMiddleware(AgentMiddleware[PlanReviewMiddlewareState]):
    """Intercepts review_plan calls and gates execution until user confirmation."""

    state_schema = PlanReviewMiddlewareState

    def _build_error_command(
        self,
        request: ToolCallRequest,
        *,
        code: str,
        message: str,
    ) -> Command:
        tool_call_id = str(request.tool_call.get("id") or _MISSING_TOOL_CALL_ID)
        tool_name = str(request.tool_call.get("name") or "unknown_tool")
        tool_message = ToolMessage(
            content=f"[{code}] {message}",
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )
        return Command(update={"messages": [tool_message]}, goto=END)

    def _build_invalid_plan_error(self, request: ToolCallRequest) -> Command:
        return self._build_error_command(
            request,
            code="PLAN_INVALID_TODOS",
            message=f"计划无效：`todos` 需要 1-{_MAX_TODOS} 条非空任务，请重新生成后再次提交审核。",
        )

    def _build_version_mismatch_command(
        self,
        request: ToolCallRequest,
        expected: int,
        got: int | None,
    ) -> Command:
        logger.info(
            "metric=plan_version_mismatch_count expected=%s got=%s",
            expected,
            got,
        )
        return self._build_error_command(
            request,
            code="PLAN_VERSION_MISMATCH",
            message=(
                f"计划版本不匹配：当前为 v{expected}，收到确认版本为 "
                f"{'空' if got is None else f'v{got}'}。请刷新后重试。"
            ),
        )

    def _build_review_required_command(self, request: ToolCallRequest) -> Command:
        logger.info("metric=plan_guard_block_count code=PLAN_REVIEW_REQUIRED")
        return self._build_error_command(
            request,
            code="PLAN_REVIEW_REQUIRED",
            message="Pro 模式要求先生成计划并调用 `review_plan` 审核，再执行任务。",
        )

    def _build_pending_review_block_command(self, request: ToolCallRequest) -> Command:
        logger.info("metric=plan_guard_block_count code=PLAN_ACTION_REQUIRED")
        return self._build_error_command(
            request,
            code="PLAN_ACTION_REQUIRED",
            message="计划处于待审核状态，请先点击“确认”或“重试”。",
        )

    def _build_terminal_state_block_command(
        self,
        request: ToolCallRequest,
        status: str,
    ) -> Command:
        logger.info(
            "metric=plan_guard_block_count code=PLAN_TERMINAL_STATE status=%s",
            status,
        )
        return self._build_error_command(
            request,
            code="PLAN_TERMINAL_STATE",
            message=f"计划已处于 `{status}` 状态，请先重试生成新计划。",
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
        updated_at = _now_ts()

        try:
            _validate_transition(
                prior.get("status") if isinstance(prior, dict) else None,
                _PLAN_EVENT_SUBMIT,
            )
        except ValueError:
            # Allow resubmit in ambiguous states by resetting to pending.
            pass

        plan_review: PlanReviewState = {
            "status": _transition(
                prior.get("status") if isinstance(prior, dict) else None,
                _PLAN_EVENT_SUBMIT,
            ),
            "version": version,
            "todos": todos,
            "updated_at": updated_at,
            "last_event_at": updated_at,
            "consecutive_failures": 0,
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
            update={"messages": [tool_message], "plan_review": plan_review, "todos": todos},
            goto=END,
        )

    def _maybe_gate_tool_call(self, request: ToolCallRequest) -> Command | None:
        tool_name = str(request.tool_call.get("name") or "")
        if tool_name == _PLAN_REVIEW_TOOL_NAME:
            return None

        plan_review = request.state.get("plan_review")
        status = plan_review.get("status") if isinstance(plan_review, dict) else None

        messages = request.state.get("messages", []) or []
        action, action_version = _normalize_plan_action(messages)
        if (
            action == _PLAN_ACTION_CONFIRM
            and isinstance(plan_review, dict)
            and status == _PLAN_STATUS_PENDING
        ):
            current_version = int(plan_review.get("version", 0))
            if action_version is not None and action_version != current_version:
                return self._build_version_mismatch_command(
                    request,
                    expected=current_version,
                    got=action_version,
                )

        if status is None:
            if _is_execution_tool(tool_name):
                return self._build_review_required_command(request)
            return None

        if status == _PLAN_STATUS_PENDING and _is_execution_tool(tool_name):
            return self._build_pending_review_block_command(request)

        if status in {_PLAN_STATUS_COMPLETED, _PLAN_STATUS_FAILED} and _is_execution_tool(tool_name):
            return self._build_terminal_state_block_command(request, status=status)

        return None

    @override
    def before_model(self, state: PlanReviewMiddlewareState, runtime) -> dict[str, Any] | None:
        if not runtime.context.get("is_plan_mode", False):
            return None

        updates: dict[str, Any] = {}
        messages = state.get("messages", []) or []
        action, action_version = _normalize_plan_action(messages)
        plan_review = state.get("plan_review")

        if action == _PLAN_ACTION_CONFIRM:
            if not isinstance(plan_review, dict):
                reminder = HumanMessage(
                    name="plan_review_confirm_missing",
                    content=(
                        "<system_reminder>\n"
                        "未找到可确认的计划，请先生成计划并提交审核。\n"
                        "</system_reminder>"
                    ),
                )
                return {"messages": [reminder]}

            status = str(plan_review.get("status", ""))
            current_version = int(plan_review.get("version", 0))
            if status != _PLAN_STATUS_PENDING:
                reminder = HumanMessage(
                    name="plan_review_confirm_invalid_status",
                    content=(
                        "<system_reminder>\n"
                        f"当前计划状态为 `{status}`，无法确认。请点击“重试”生成新计划。\n"
                        "</system_reminder>"
                    ),
                )
                return {"messages": [reminder]}

            if action_version is not None and action_version != current_version:
                updated = {
                    **plan_review,
                    "error_code": "PLAN_VERSION_MISMATCH",
                    "error_message": (
                        f"版本冲突：当前 v{current_version}，收到 v{action_version}。"
                    ),
                    "updated_at": _now_ts(),
                    "last_event_at": _now_ts(),
                }
                reminder = HumanMessage(
                    name="plan_review_confirm_version_mismatch",
                    content=(
                        "<system_reminder>\n"
                        f"计划版本不匹配（当前 v{current_version}，收到 v{action_version}），请刷新后重试。\n"
                        "</system_reminder>"
                    ),
                )
                return {"plan_review": updated, "messages": [reminder]}

            _validate_transition(status, _PLAN_EVENT_CONFIRM)
            pending_since = int(plan_review.get("updated_at", 0) or 0)
            now_ts = _now_ts()
            if pending_since > 0:
                duration_ms = max(0, (now_ts - pending_since) * 1000)
                logger.info(
                    "metric=pending_review_duration_ms duration_ms=%s version=%s",
                    duration_ms,
                    current_version,
                )
            updated_review = {
                **plan_review,
                "status": _transition(status, _PLAN_EVENT_CONFIRM),
                "updated_at": now_ts,
                "last_event_at": now_ts,
                "error_code": "",
                "error_message": "",
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
            updates["plan_review"] = updated_review
            updates["todos"] = todos
            updates["messages"] = [reminder]

        elif action == _PLAN_ACTION_RETRY:
            if isinstance(plan_review, dict):
                status = str(plan_review.get("status", ""))
                try:
                    _validate_transition(status, _PLAN_EVENT_RETRY)
                    next_status = _transition(status, _PLAN_EVENT_RETRY)
                except ValueError:
                    next_status = _PLAN_STATUS_PENDING
                updated_review = {
                    **plan_review,
                    "status": next_status,
                    "updated_at": _now_ts(),
                    "last_event_at": _now_ts(),
                    "error_code": "",
                    "error_message": "",
                }
                updates["plan_review"] = updated_review
            reminder = HumanMessage(
                name="plan_review_retry",
                content=(
                    "<system_reminder>\n"
                    "用户要求重试计划。请先重新整理 todo 计划，再调用 `review_plan` 进入下一轮审核。"
                    "在新计划获批前，不要执行计划任务。\n"
                    "</system_reminder>"
                ),
            )
            updates["messages"] = [reminder]

        if isinstance(plan_review, dict):
            status = str(plan_review.get("status", ""))
            if status in {_PLAN_STATUS_APPROVED, _PLAN_STATUS_EXECUTING} and _all_todos_completed(state):
                try:
                    _validate_transition(status, _PLAN_EVENT_EXECUTION_COMPLETED)
                    completed_status = _transition(status, _PLAN_EVENT_EXECUTION_COMPLETED)
                except ValueError:
                    completed_status = _PLAN_STATUS_COMPLETED
                todos = state.get("todos")
                if not isinstance(todos, list):
                    todos = plan_review.get("todos", [])
                updates["plan_review"] = {
                    **plan_review,
                    "status": completed_status,
                    "todos": todos,
                    "updated_at": _now_ts(),
                    "last_event_at": _now_ts(),
                    "error_code": "",
                    "error_message": "",
                }

        return updates or None

    def _post_tool_updates(
        self,
        request: ToolCallRequest,
        *,
        tool_name: str,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        plan_review = request.state.get("plan_review")
        if not isinstance(plan_review, dict):
            return updates

        status = str(plan_review.get("status", ""))
        if status == _PLAN_STATUS_APPROVED and _is_execution_tool(tool_name):
            try:
                _validate_transition(status, _PLAN_EVENT_EXECUTION_STARTED)
                next_status = _transition(status, _PLAN_EVENT_EXECUTION_STARTED)
            except ValueError:
                next_status = _PLAN_STATUS_EXECUTING
            updates["plan_review"] = {
                **plan_review,
                "status": next_status,
                "updated_at": _now_ts(),
                "last_event_at": _now_ts(),
                "error_code": "",
                "error_message": "",
            }

        if tool_name == "write_todos":
            raw_args = request.tool_call.get("args", {})
            raw_args = _parse_json_string(raw_args)
            if isinstance(raw_args, dict):
                normalized = _normalize_todos(raw_args.get("todos"))
                if normalized:
                    base = updates.get("plan_review", plan_review)
                    updates["plan_review"] = {
                        **base,
                        "todos": normalized,
                        "updated_at": _now_ts(),
                        "last_event_at": _now_ts(),
                    }
                    updates["todos"] = normalized

        return updates

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        tool_name = str(request.tool_call.get("name") or "")
        if tool_name == _PLAN_REVIEW_TOOL_NAME:
            return self._handle_review_plan(request)

        gate_result = self._maybe_gate_tool_call(request)
        if gate_result is not None:
            return gate_result

        result = handler(request)
        updates = self._post_tool_updates(request, tool_name=tool_name)
        if not updates:
            return result

        if isinstance(result, Command):
            return _merge_command_update(result, updates)

        return Command(update={"messages": [result], **updates})

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        tool_name = str(request.tool_call.get("name") or "")
        if tool_name == _PLAN_REVIEW_TOOL_NAME:
            return self._handle_review_plan(request)

        gate_result = self._maybe_gate_tool_call(request)
        if gate_result is not None:
            return gate_result

        result = await handler(request)
        updates = self._post_tool_updates(request, tool_name=tool_name)
        if not updates:
            return result

        if isinstance(result, Command):
            return _merge_command_update(result, updates)

        return Command(update={"messages": [result], **updates})
