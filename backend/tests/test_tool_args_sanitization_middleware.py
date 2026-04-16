from types import SimpleNamespace

from deerflow.agents.middlewares.tool_args_sanitization_middleware import (
    ToolArgsSanitizationMiddleware,
)


def _runtime():
    return SimpleNamespace(context={"thread_id": "t-1"})


def test_sanitizes_json_string_args():
    middleware = ToolArgsSanitizationMiddleware()
    state = {
        "messages": [
            SimpleNamespace(
                type="ai",
                content="",
                tool_calls=[
                    {
                        "id": "tc-1",
                        "name": "read_file",
                        "args": '{"path":"/tmp/a.txt"}',
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }

    update = middleware.after_model(state, _runtime())
    assert update is not None
    updated = update["messages"][0]
    assert updated.tool_calls[0]["args"]["path"] == "/tmp/a.txt"
    assert update["messages"][1].name == "tool_args_repaired"


def test_drops_unrecoverable_args():
    middleware = ToolArgsSanitizationMiddleware()
    state = {
        "messages": [
            SimpleNamespace(
                type="ai",
                content="",
                tool_calls=[
                    {
                        "id": "tc-1",
                        "name": "read_file",
                        "args": "not-json",
                        "type": "tool_call",
                    },
                    {
                        "id": "tc-2",
                        "name": "write_todos",
                        "args": {"todos": [{"content": "ok"}]},
                        "type": "tool_call",
                    },
                ],
            )
        ]
    }

    update = middleware.after_model(state, _runtime())
    assert update is not None
    updated = update["messages"][0]
    tool_names = [tc["name"] for tc in updated.tool_calls]
    assert tool_names == ["write_todos"]
