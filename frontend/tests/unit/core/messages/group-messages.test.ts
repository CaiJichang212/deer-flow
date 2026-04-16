import { expect, test } from "vitest";

import { groupMessages } from "@/core/messages/utils";

test("groups review_plan tool message into assistant:plan-review", () => {
  const messages = [
    {
      id: "ai-1",
      type: "ai",
      content: "",
      tool_calls: [{ id: "tc-1", name: "review_plan", args: { todos: [] } }],
    },
    {
      id: "tool-1",
      type: "tool",
      name: "review_plan",
      content: "plan",
      tool_call_id: "tc-1",
    },
  ] as any[];

  const groups = groupMessages(messages as any, (group) => group.type);
  expect(groups).toContain("assistant:plan-review");
});

test("ignores hidden plan_action message", () => {
  const messages = [
    {
      id: "h-1",
      type: "human",
      content: "",
      additional_kwargs: {
        hide_from_ui: true,
        plan_action: "confirm",
        plan_version: 1,
      },
    },
  ] as any[];

  const groups = groupMessages(messages as any, (group) => group);
  expect(groups).toHaveLength(0);
});

