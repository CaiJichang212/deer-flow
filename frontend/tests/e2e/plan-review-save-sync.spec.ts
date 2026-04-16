import { expect, test } from "@playwright/test";

const threadId = "playwright-plan-review-sync";

function buildHistoryResponse() {
  return [
    {
      values: {
        title: "Playwright Plan Review",
        artifacts: [],
        todos: [
          { content: "收集贵州茅台公司概况信息", status: "pending" },
          { content: "分析财务数据（2025全年及2026Q1）", status: "pending" },
        ],
        plan_review: {
          status: "pending_review",
          version: 1,
          title: "贵州茅台（600519.SH）八维度全面投资分析计划",
          updated_at: 1_760_000_000,
          todos: [
            { content: "收集贵州茅台公司概况信息" },
            { content: "分析财务数据（2025全年及2026Q1）" },
          ],
        },
        messages: [
          {
            id: "human-1",
            type: "human",
            content: "请先给出计划并等待我审核。",
            additional_kwargs: {},
            response_metadata: {},
          },
          {
            id: "ai-1",
            type: "ai",
            content: "",
            name: null,
            additional_kwargs: {},
            response_metadata: {},
            tool_calls: [
              {
                id: "review_plan:1",
                name: "review_plan",
                args: {
                  title: "贵州茅台（600519.SH）八维度全面投资分析计划",
                  todos: [
                    { content: "收集贵州茅台公司概况信息" },
                    { content: "分析财务数据（2025全年及2026Q1）" },
                  ],
                },
                type: "tool_call",
              },
            ],
            invalid_tool_calls: [],
            usage_metadata: null,
          },
          {
            id: "tool-1",
            type: "tool",
            name: "review_plan",
            tool_call_id: "review_plan:1",
            content: "Plan submitted for user review",
            additional_kwargs: {},
            response_metadata: {},
            artifact: null,
            status: "success",
          },
        ],
      },
      next: [],
      tasks: [],
      metadata: {},
      created_at: "2026-04-16T10:00:00.000Z",
      checkpoint: {},
      parent_checkpoint: null,
      interrupts: [],
      checkpoint_id: "cp-1",
      parent_checkpoint_id: null,
    },
  ];
}

test("编辑计划保存后，计划卡片和 To-dos 同步为同一份内容", async ({ page }) => {
  let savedPayload: any = null;

  await page.route(`**/mock/api/threads/${threadId}/history`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildHistoryResponse()),
    });
  });

  await page.route(`**/api/threads/${threadId}/state`, async (route) => {
    const postData = route.request().postData();
    savedPayload = postData ? JSON.parse(postData) : null;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.goto(`/workspace/chats/${threadId}?mock=true`);

  const card = page.getByTestId("plan-review-card");
  await expect(card).toBeVisible();

  await page.getByTestId("plan-review-edit").click();
  await page
    .getByTestId("plan-review-input-0")
    .fill("收集贵州茅台公司概况信息（已编辑）");
  await page.getByTestId("plan-review-save").click();

  await expect(page.getByTestId("plan-review-item-0")).toContainText(
    "收集贵州茅台公司概况信息（已编辑）",
  );

  await page.getByTestId("todo-list-header").click();
  await expect(page.getByTestId("todo-list-item-0")).toContainText(
    "收集贵州茅台公司概况信息（已编辑）",
  );

  await expect
    .poll(() => savedPayload?.values?.plan_review?.todos?.[0]?.content ?? null)
    .toBe("收集贵州茅台公司概况信息（已编辑）");
  await expect
    .poll(() => savedPayload?.values?.todos?.[0]?.content ?? null)
    .toBe("收集贵州茅台公司概况信息（已编辑）");

  expect(savedPayload).not.toBeNull();
  if (!savedPayload) {
    throw new Error("save payload is missing");
  }
  expect(savedPayload.values?.plan_review?.todos).toEqual(
    savedPayload.values?.todos,
  );
});
