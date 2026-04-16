from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from deerflow.agents.middlewares.plan_execution_guard_middleware import (
    PlanExecutionGuardMiddleware,
)
from deerflow.agents.middlewares.todo_middleware import TodoMiddleware


def _runtime():
    return SimpleNamespace(context={"thread_id": "t-1"})


def test_consecutive_failures_set_plan_failed():
    middleware = PlanExecutionGuardMiddleware(max_consecutive_failures=2)
    state = {
        "plan_review": {
            "status": "executing",
            "version": 1,
            "todos": [{"content": "a", "status": "in_progress"}],
            "updated_at": 1,
        },
        "messages": [
            AIMessage(content="LLM request failed: xxx"),
            AIMessage(content="LLM request failed: yyy"),
        ],
    }

    update = middleware.after_model(state, _runtime())
    assert update is not None
    assert update["plan_review"]["status"] == "failed"
    assert update["plan_review"]["error_code"] == "PLAN_EXECUTION_FAILED"
    assert update["messages"][0].name == "plan_execution_failed"


def test_todo_middleware_skips_completion_reminder_when_plan_failed():
    middleware = TodoMiddleware(system_prompt="", tool_description="")
    state = {
        "plan_review": {
            "status": "failed",
            "version": 1,
            "todos": [{"content": "a", "status": "in_progress"}],
            "updated_at": 1,
        },
        "todos": [{"content": "a", "status": "in_progress"}],
        "messages": [AIMessage(content="final answer", tool_calls=[])],
    }
    result = middleware.after_model(state, _runtime())
    assert result is None

