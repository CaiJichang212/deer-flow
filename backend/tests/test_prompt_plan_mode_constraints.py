from deerflow.agents.lead_agent.prompt import apply_prompt_template


def test_plan_mode_prompt_contains_stage_tool_constraints():
    prompt = apply_prompt_template(is_plan_mode=True)
    assert "Before approval (`pending_review`), only use" in prompt
    assert "Execution quality constraints" in prompt
    assert "include credible sources and explicit dates" in prompt

