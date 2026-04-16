from types import SimpleNamespace

from langchain_core.messages import ToolMessage
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from deerflow.agents.middlewares.plan_review_middleware import PlanReviewMiddleware


def _request(
    *,
    name: str,
    args: dict | None = None,
    tool_call_id: str = "tc-1",
    state: dict | None = None,
):
    return SimpleNamespace(
        tool_call={
            "name": name,
            "id": tool_call_id,
            "args": args or {},
        },
        state=state or {},
    )


def _runtime(is_plan_mode: bool = True):
    return SimpleNamespace(context={"is_plan_mode": is_plan_mode})


def test_review_plan_call_writes_state_and_interrupts():
    middleware = PlanReviewMiddleware()
    request = _request(
        name="review_plan",
        args={"todos": [{"content": "step 1"}, {"content": "step 2", "status": "pending"}]},
    )

    result = middleware.wrap_tool_call(request, lambda _req: None)

    assert isinstance(result, Command)
    assert result.goto == "__end__"
    update = result.update
    assert update is not None
    assert update["plan_review"]["status"] == "pending_review"
    assert update["plan_review"]["version"] == 1
    assert len(update["plan_review"]["todos"]) == 2
    assert update["todos"] == update["plan_review"]["todos"]
    assert update["messages"][0].name == "review_plan"


def test_review_plan_rejects_empty_todos_and_keeps_review_gate():
    middleware = PlanReviewMiddleware()
    request = _request(name="review_plan", args={"todos": []})

    result = middleware.wrap_tool_call(request, lambda _req: None)

    assert isinstance(result, Command)
    assert result.goto == "__end__"
    update = result.update
    assert update is not None
    assert "plan_review" not in update
    assert update["messages"][0].status == "error"


def test_pending_review_blocks_execution_without_confirm():
    middleware = PlanReviewMiddleware()
    request = _request(
        name="read_file",
        state={
            "plan_review": {
                "status": "pending_review",
                "version": 2,
                "todos": [{"content": "do it"}],
                "updated_at": 1,
            },
            "messages": [HumanMessage(content="继续", additional_kwargs={})],
        },
    )

    result = middleware.wrap_tool_call(request, lambda _req: "should-not-run")

    assert isinstance(result, Command)
    assert result.goto == "__end__"
    assert result.update["messages"][0].status == "error"
    assert "PLAN_ACTION_REQUIRED" in result.update["messages"][0].text


def test_pro_mode_requires_review_plan_before_execution():
    middleware = PlanReviewMiddleware()
    request = _request(
        name="read_file",
        state={
            "messages": [HumanMessage(content="请帮我做这个任务")],
        },
    )

    result = middleware.wrap_tool_call(request, lambda _req: "should-not-run")

    assert isinstance(result, Command)
    assert result.goto == "__end__"
    assert "review_plan" in result.update["messages"][0].text


def test_confirm_transitions_to_executing_and_allows_execution():
    middleware = PlanReviewMiddleware()
    state = {
        "plan_review": {
            "status": "pending_review",
            "version": 3,
            "todos": [{"content": "a"}, {"content": "b"}],
            "updated_at": 1,
        },
        "messages": [
            HumanMessage(
                content="",
                additional_kwargs={
                    "hide_from_ui": True,
                    "plan_action": "confirm",
                    "plan_version": 3,
                },
            )
        ],
    }

    before_update = middleware.before_model(state, _runtime())
    assert before_update is not None
    assert before_update["plan_review"]["status"] == "approved"
    assert before_update["todos"] == before_update["plan_review"]["todos"]

    request = _request(name="read_file", state={**state, **before_update})
    result = middleware.wrap_tool_call(
        request,
        lambda _req: ToolMessage(content="ok", tool_call_id="tc-1", name="read_file"),
    )
    assert isinstance(result, Command)
    assert result.update["plan_review"]["status"] == "executing"


def test_retry_keeps_pending_and_only_allows_planning_tools():
    middleware = PlanReviewMiddleware()
    state = {
        "plan_review": {
            "status": "pending_review",
            "version": 1,
            "todos": [{"content": "old plan"}],
            "updated_at": 1,
        },
        "messages": [
            HumanMessage(
                content="",
                additional_kwargs={
                    "hide_from_ui": True,
                    "plan_action": "retry",
                    "plan_version": 1,
                },
            )
        ],
    }

    before_update = middleware.before_model(state, _runtime())
    assert before_update is not None
    assert before_update["plan_review"]["status"] == "pending_review"
    assert before_update["plan_review"]["error_code"] == ""
    assert before_update["plan_review"]["error_message"] == ""
    assert before_update["messages"][0].name == "plan_review_retry"

    blocked = middleware.wrap_tool_call(_request(name="read_file", state=state), lambda _req: "x")
    assert isinstance(blocked, Command)
    allowed = middleware.wrap_tool_call(_request(name="write_todos", state=state), lambda _req: "ok")
    assert allowed == "ok"


def test_confirm_version_mismatch_blocks_execution():
    middleware = PlanReviewMiddleware()
    state = {
        "plan_review": {
            "status": "pending_review",
            "version": 3,
            "todos": [{"content": "a"}],
            "updated_at": 1,
        },
        "messages": [
            HumanMessage(
                content="",
                additional_kwargs={
                    "hide_from_ui": True,
                    "plan_action": "confirm",
                    "plan_version": 2,
                },
            )
        ],
    }

    before_update = middleware.before_model(state, _runtime())
    assert before_update is not None
    assert before_update["plan_review"]["status"] == "pending_review"
    assert before_update["plan_review"]["error_code"] == "PLAN_VERSION_MISMATCH"


def test_terminal_states_block_execution_tools():
    middleware = PlanReviewMiddleware()
    for status in ("completed", "failed"):
        request = _request(
            name="read_file",
            state={
                "plan_review": {
                    "status": status,
                    "version": 1,
                    "todos": [{"content": "a"}],
                    "updated_at": 1,
                },
                "messages": [HumanMessage(content="继续")],
            },
        )
        result = middleware.wrap_tool_call(request, lambda _req: "x")
        assert isinstance(result, Command)
        assert result.goto == "__end__"
        assert "PLAN_TERMINAL_STATE" in result.update["messages"][0].text
