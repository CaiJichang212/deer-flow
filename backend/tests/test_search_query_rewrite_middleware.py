from types import SimpleNamespace

from langchain_core.messages import ToolMessage

from deerflow.agents.middlewares.search_query_rewrite_middleware import (
    SearchQueryRewriteMiddleware,
)


def _request(query: str):
    return SimpleNamespace(
        tool_call={
            "id": "tc-1",
            "name": "web_search",
            "args": {"query": query},
        },
        state={},
        runtime=SimpleNamespace(context={"thread_id": "t-1"}),
    )


def test_rewrites_finance_query():
    middleware = SearchQueryRewriteMiddleware()
    captured_queries = []

    def handler(request):
        captured_queries.append(request.tool_call["args"]["query"])
        return ToolMessage(
            content={"results": [{"title": "random", "content": "noise"}]},
            tool_call_id="tc-1",
            name="web_search",
        )

    middleware.wrap_tool_call(_request("贵州茅台 PE PB 2026"), handler)
    assert len(captured_queries) >= 1
    assert "site:eastmoney.com" in captured_queries[0]

