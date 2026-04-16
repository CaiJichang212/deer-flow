"""Rewrite and optionally refine low-quality web_search queries."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from typing import Any, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

logger = logging.getLogger(__name__)

_FINANCE_HINT = " site:eastmoney.com OR site:sina.com.cn OR site:cninfo.com.cn"
_TRAVEL_HINT = " 官方 攻略 交通 营业时间"


def _parse_args(raw_args: Any) -> dict[str, Any]:
    if isinstance(raw_args, dict):
        return dict(raw_args)
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[\s,，。:：()（）]+", text) if len(token) >= 2]


def _rewrite_query(query: str) -> str:
    q = query.strip()
    if not q:
        return q
    lowered = q.lower()
    if any(k in q for k in ("茅台", "股价", "PE", "PB", "估值")) and "site:" not in lowered:
        q = q + _FINANCE_HINT
    if any(k in q for k in ("旅游", "园林", "古建筑", "周末", "行程")) and "攻略" not in q:
        q = q + _TRAVEL_HINT
    if "2026" in q and "最新" not in q:
        q = q + " 最新"
    return q


def _extract_results(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, dict):
        results = content.get("results")
        return results if isinstance(results, list) else []
    if isinstance(content, list):
        return [r for r in content if isinstance(r, dict)]
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except Exception:
            return []
        return _extract_results(parsed)
    return []


def _is_low_quality(query: str, tool_message: ToolMessage) -> bool:
    query_tokens = _tokenize(query)
    if len(query_tokens) == 0:
        return False

    results = _extract_results(tool_message.content)
    if len(results) == 0:
        return True

    sample = results[:3]
    hit = 0
    total = len(query_tokens) * len(sample)
    if total == 0:
        return False
    for result in sample:
        blob = f"{result.get('title', '')} {result.get('content', '')}".lower()
        for token in query_tokens:
            if token.lower() in blob:
                hit += 1
    score = hit / total
    return score < 0.15


class SearchQueryRewriteMiddleware(AgentMiddleware[AgentState]):
    """Improve web_search query quality and run at most one refined retry."""

    def _clone_request(self, request: ToolCallRequest, tool_call: dict[str, Any]) -> ToolCallRequest:
        return SimpleNamespace(
            tool_call=tool_call,
            state=request.state,
            runtime=request.runtime,
        )

    def _prepare_call(self, request: ToolCallRequest, query: str, *, refined_once: bool) -> ToolCallRequest:
        tool_call = dict(request.tool_call)
        args = _parse_args(tool_call.get("args"))
        args["query"] = query
        if refined_once:
            args["__refined_once"] = True
        tool_call["args"] = args
        return self._clone_request(request, tool_call)

    def _run_refine_once(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
        first_result: ToolMessage | Command,
        current_query: str,
    ) -> ToolMessage | Command:
        if not isinstance(first_result, ToolMessage):
            return first_result
        args = _parse_args(request.tool_call.get("args"))
        if args.get("__refined_once"):
            return first_result
        if not _is_low_quality(current_query, first_result):
            return first_result

        refined = _rewrite_query(current_query)
        if refined == current_query:
            return first_result

        logger.info("metric=search_query_refine_retry query=%s refined=%s", current_query, refined)
        refined_request = self._prepare_call(request, refined, refined_once=True)
        return handler(refined_request)

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        if request.tool_call.get("name") != "web_search":
            return handler(request)

        args = _parse_args(request.tool_call.get("args"))
        raw_query = str(args.get("query", "")).strip()
        rewritten = _rewrite_query(raw_query)
        next_request = self._prepare_call(
            request,
            rewritten if rewritten else raw_query,
            refined_once=bool(args.get("__refined_once")),
        )
        result = handler(next_request)
        return self._run_refine_once(next_request, handler, result, rewritten or raw_query)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        if request.tool_call.get("name") != "web_search":
            return await handler(request)

        args = _parse_args(request.tool_call.get("args"))
        raw_query = str(args.get("query", "")).strip()
        rewritten = _rewrite_query(raw_query)
        next_request = self._prepare_call(
            request,
            rewritten if rewritten else raw_query,
            refined_once=bool(args.get("__refined_once")),
        )
        result = await handler(next_request)
        if not isinstance(result, ToolMessage):
            return result
        if args.get("__refined_once") or not _is_low_quality(rewritten or raw_query, result):
            return result
        refined = _rewrite_query(rewritten or raw_query)
        if refined == (rewritten or raw_query):
            return result
        logger.info("metric=search_query_refine_retry query=%s refined=%s", rewritten or raw_query, refined)
        refined_request = self._prepare_call(next_request, refined, refined_once=True)
        return await handler(refined_request)

