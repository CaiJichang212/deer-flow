from types import SimpleNamespace

from langchain_core.messages import AIMessage

from deerflow.agents.middlewares.plan_tool_whitelist_middleware import (
    PlanToolWhitelistMiddleware,
)


def test_filters_non_planning_tools_in_pending_review():
    middleware = PlanToolWhitelistMiddleware()
    state = {
        "plan_review": {
            "status": "pending_review",
            "version": 1,
            "todos": [{"content": "a"}],
            "updated_at": 1,
        },
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"id": "1", "name": "web_search", "args": {"query": "x"}},
                    {"id": "2", "name": "review_plan", "args": {"todos": [{"content": "a"}]}},
                ],
            )
        ],
    }
    runtime = SimpleNamespace(context={"thread_id": "t-1"})

    update = middleware.after_model(state, runtime)
    assert update is not None
    updated = update["messages"][0]
    assert [tc["name"] for tc in updated.tool_calls] == ["review_plan"]
    assert update["messages"][1].name == "plan_tool_filtered"

