from langchain.tools import tool


@tool("review_plan", parse_docstring=True, return_direct=True)
def review_plan_tool(
    todos: list[dict[str, str]],
    title: str | None = None,
) -> str:
    """Submit a plan for user review before execution.

    In Pro mode, after you finish the initial planning phase, you MUST call this
    tool to pause execution and wait for the user's decision.

    Use this only for plan-review handoff:
    1. First generate/update todos (typically via `write_todos`).
    2. Then call `review_plan` with the plan snapshot to request approval.
    3. Do NOT execute plan tasks until user confirms.

    Args:
        todos: Plan todo items for review. Must contain at least one non-empty item.
            Each item should include a `content` field, and may include `status`.
        title: Optional short plan title shown in review UI.
    """
    # Intercepted by PlanReviewMiddleware.
    return "Plan review request processed by middleware"

