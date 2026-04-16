from types import SimpleNamespace

from deerflow.agents.middlewares.llm_error_handling_middleware import (
    LLMErrorHandlingMiddleware,
)


class APITimeoutError(Exception):
    pass


def test_thread_level_fallback_soft_and_hard():
    middleware = LLMErrorHandlingMiddleware()
    middleware.retry_max_attempts = 1
    request = SimpleNamespace(runtime=SimpleNamespace(context={"thread_id": "thread-a"}))

    def always_fail(_request):
        raise APITimeoutError("timeout")

    first = middleware.wrap_model_call(request, always_fail)
    assert "temporarily unavailable" in first.content.lower() or "request failed" in first.content.lower()

    second = middleware.wrap_model_call(request, always_fail)
    assert "连续模型失败" in second.content

    third = middleware.wrap_model_call(request, always_fail)
    assert "连续失败" in third.content and "保护模式" in third.content

