"""Middleware for automatic thread title generation."""

import logging
import re
from typing import NotRequired, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

from deerflow.config.title_config import get_title_config
from deerflow.models import create_chat_model

logger = logging.getLogger(__name__)
_HARD_TITLE_CHAR_LIMIT = 10


class TitleMiddlewareState(AgentState):
    """Compatible with the `ThreadState` schema."""

    title: NotRequired[str | None]


class TitleMiddleware(AgentMiddleware[TitleMiddlewareState]):
    """Automatically generate a title for the thread after the first user message."""

    state_schema = TitleMiddlewareState

    def _effective_max_chars(self) -> int:
        config = get_title_config()
        return min(config.max_chars, _HARD_TITLE_CHAR_LIMIT)

    def _normalize_content(self, content: object) -> str:
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts = [self._normalize_content(item) for item in content]
            return "\n".join(part for part in parts if part)

        if isinstance(content, dict):
            text_value = content.get("text")
            if isinstance(text_value, str):
                return text_value

            nested_content = content.get("content")
            if nested_content is not None:
                return self._normalize_content(nested_content)

        return ""

    def _should_generate_title(self, state: TitleMiddlewareState) -> bool:
        """Check if we should generate a title for this thread."""
        config = get_title_config()
        if not config.enabled:
            return False

        # Check if thread already has a title in state
        if state.get("title"):
            return False

        # Check if this is the first turn (has at least one user message and one assistant response)
        messages = state.get("messages", [])
        if len(messages) < 2:
            return False

        # Count user and assistant messages
        user_messages = [m for m in messages if m.type == "human"]
        assistant_messages = [m for m in messages if m.type == "ai"]

        # Generate title after first complete exchange
        return len(user_messages) == 1 and len(assistant_messages) >= 1

    def _build_title_prompt(self, state: TitleMiddlewareState) -> tuple[str, str]:
        """Extract user/assistant messages and build the title prompt.

        Returns (prompt_string, user_msg) so callers can use user_msg as fallback.
        """
        config = get_title_config()
        messages = state.get("messages", [])

        user_msg_content = next((m.content for m in messages if m.type == "human"), "")
        assistant_msg_content = next((m.content for m in messages if m.type == "ai"), "")

        user_msg = self._normalize_content(user_msg_content)
        assistant_msg = self._strip_think_tags(self._normalize_content(assistant_msg_content))

        prompt = config.prompt_template.format(
            max_words=config.max_words,
            max_chars=self._effective_max_chars(),
            user_msg=user_msg[:240],
            assistant_msg=assistant_msg[:240],
        )
        return prompt, user_msg

    def _strip_think_tags(self, text: str) -> str:
        """Remove <think>...</think> blocks emitted by reasoning models (e.g. minimax, DeepSeek-R1)."""
        return re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()

    def _parse_title(self, content: object) -> str:
        """Normalize model output into a clean title string."""
        title_content = self._normalize_content(content)
        title_content = self._strip_think_tags(title_content)
        # Keep only the first non-empty line to avoid verbose multi-line output.
        lines = [line.strip() for line in title_content.splitlines() if line.strip()]
        title = lines[0] if lines else ""
        # Strip common prefixes.
        title = re.sub(r"^(title|标题|输出|output)\s*[:：]\s*", "", title, flags=re.IGNORECASE).strip()
        title = title.strip('"').strip("'")
        max_chars = self._effective_max_chars()
        return title[:max_chars] if len(title) > max_chars else title

    def _fallback_title(self, user_msg: str) -> str:
        max_chars = self._effective_max_chars()
        if not user_msg:
            return "New Chat"[:max_chars]
        return user_msg[:max_chars]

    def _generate_title_result(self, state: TitleMiddlewareState) -> dict | None:
        """Generate a local fallback title without blocking on an LLM call."""
        if not self._should_generate_title(state):
            return None

        _, user_msg = self._build_title_prompt(state)
        return {"title": self._fallback_title(user_msg)}

    async def _agenerate_title_result(self, state: TitleMiddlewareState) -> dict | None:
        """Generate a title asynchronously and fall back locally on failure."""
        if not self._should_generate_title(state):
            return None

        config = get_title_config()
        prompt, user_msg = self._build_title_prompt(state)

        try:
            if config.model_name:
                model = create_chat_model(
                    name=config.model_name,
                    thinking_enabled=False,
                    reasoning_effort="minimal",
                )
            else:
                model = create_chat_model(
                    thinking_enabled=False,
                    reasoning_effort="minimal",
                )
            response = await model.ainvoke(prompt)
            title = self._parse_title(response.content)
            if title:
                return {"title": title}
        except Exception:
            logger.debug("Failed to generate async title; falling back to local title", exc_info=True)
        return {"title": self._fallback_title(user_msg)}

    @override
    def after_model(self, state: TitleMiddlewareState, runtime: Runtime) -> dict | None:
        return self._generate_title_result(state)

    @override
    async def aafter_model(self, state: TitleMiddlewareState, runtime: Runtime) -> dict | None:
        return await self._agenerate_title_result(state)
