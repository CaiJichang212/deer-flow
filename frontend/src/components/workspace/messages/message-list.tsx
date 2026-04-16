import type { BaseStream } from "@langchain/langgraph-sdk/react";
import { useMemo, useState } from "react";

import {
  Conversation,
  ConversationContent,
} from "@/components/ai-elements/conversation";
import { useI18n } from "@/core/i18n/hooks";
import {
  extractContentFromMessage,
  extractPresentFilesFromMessage,
  extractTextFromMessage,
  groupMessages,
  hasContent,
  hasPresentFiles,
  hasReasoning,
} from "@/core/messages/utils";
import { useRehypeSplitWordsIntoSpans } from "@/core/rehype";
import type { Subtask } from "@/core/tasks";
import { useUpdateSubtask } from "@/core/tasks/context";
import type { AgentThreadState } from "@/core/threads";
import type { PlanReviewState } from "@/core/threads";
import type { PlanReviewTodo } from "@/core/threads";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

import { ArtifactFileList } from "../artifacts/artifact-file-list";
import { StreamingIndicator } from "../streaming-indicator";

import { MarkdownContent } from "./markdown-content";
import { MessageGroup } from "./message-group";
import { MessageListItem } from "./message-list-item";
import { MessageListSkeleton } from "./skeleton";
import { SubtaskCard } from "./subtask-card";

export const MESSAGE_LIST_DEFAULT_PADDING_BOTTOM = 160;
export const MESSAGE_LIST_FOLLOWUPS_EXTRA_PADDING_BOTTOM = 80;

export function MessageList({
  className,
  threadId,
  thread,
  paddingBottom = MESSAGE_LIST_DEFAULT_PADDING_BOTTOM,
  onPlanAction,
  onPlanSave,
  planReviewOverride,
}: {
  className?: string;
  threadId: string;
  thread: BaseStream<AgentThreadState>;
  paddingBottom?: number;
  onPlanAction?: (action: "confirm" | "retry", planVersion: number) => void;
  onPlanSave?: (
    todos: PlanReviewTodo[],
    planVersion: number,
  ) => Promise<boolean> | boolean;
  planReviewOverride?: PlanReviewState | null;
}) {
  const { t } = useI18n();
  const rehypePlugins = useRehypeSplitWordsIntoSpans(thread.isLoading);
  const updateSubtask = useUpdateSubtask();
  const messages = thread.messages;
  const planReviewForUI = planReviewOverride ?? thread.values.plan_review;
  if (thread.isThreadLoading && messages.length === 0) {
    return <MessageListSkeleton />;
  }
  return (
    <Conversation
      className={cn("flex size-full flex-col justify-center", className)}
    >
      <ConversationContent className="mx-auto w-full max-w-(--container-width-md) gap-8 pt-12">
        {groupMessages(messages, (group) => {
          if (group.type === "human" || group.type === "assistant") {
            return group.messages.map((msg) => {
              return (
                <MessageListItem
                  key={`${group.id}/${msg.id}`}
                  message={msg}
                  isLoading={thread.isLoading}
                  threadId={threadId}
                />
              );
            });
          } else if (group.type === "assistant:clarification") {
            const message = group.messages[0];
            if (message && hasContent(message)) {
              return (
                <MarkdownContent
                  key={group.id}
                  content={extractContentFromMessage(message)}
                  isLoading={thread.isLoading}
                  rehypePlugins={rehypePlugins}
                />
              );
            }
            return null;
          } else if (group.type === "assistant:plan-review") {
            const planReview = planReviewForUI;
            if (
              !planReview ||
              (planReview.status !== "pending_review" &&
                planReview.status !== "failed")
            ) {
              return null;
            }
            return (
              <PlanReviewCard
                key={group.id}
                todos={planReview.todos ?? []}
                version={planReview.version ?? 0}
                title={planReview.title}
                status={planReview.status}
                errorCode={planReview.error_code}
                errorMessage={planReview.error_message}
                onAction={onPlanAction}
                onSave={onPlanSave}
              />
            );
          } else if (group.type === "assistant:present-files") {
            const files: string[] = [];
            for (const message of group.messages) {
              if (hasPresentFiles(message)) {
                const presentFiles = extractPresentFilesFromMessage(message);
                files.push(...presentFiles);
              }
            }
            return (
              <div className="w-full" key={group.id}>
                {group.messages[0] && hasContent(group.messages[0]) && (
                  <MarkdownContent
                    content={extractContentFromMessage(group.messages[0])}
                    isLoading={thread.isLoading}
                    rehypePlugins={rehypePlugins}
                    className="mb-4"
                  />
                )}
                <ArtifactFileList files={files} threadId={threadId} />
              </div>
            );
          } else if (group.type === "assistant:subagent") {
            const tasks = new Set<Subtask>();
            for (const message of group.messages) {
              if (message.type === "ai") {
                for (const toolCall of message.tool_calls ?? []) {
                  if (toolCall.name === "task") {
                    const task: Subtask = {
                      id: toolCall.id!,
                      subagent_type: toolCall.args.subagent_type,
                      description: toolCall.args.description,
                      prompt: toolCall.args.prompt,
                      status: "in_progress",
                    };
                    updateSubtask(task);
                    tasks.add(task);
                  }
                }
              } else if (message.type === "tool") {
                const taskId = message.tool_call_id;
                if (taskId) {
                  const result = extractTextFromMessage(message);
                  if (result.startsWith("Task Succeeded. Result:")) {
                    updateSubtask({
                      id: taskId,
                      status: "completed",
                      result: result
                        .split("Task Succeeded. Result:")[1]
                        ?.trim(),
                    });
                  } else if (result.startsWith("Task failed.")) {
                    updateSubtask({
                      id: taskId,
                      status: "failed",
                      error: result.split("Task failed.")[1]?.trim(),
                    });
                  } else if (result.startsWith("Task timed out")) {
                    updateSubtask({
                      id: taskId,
                      status: "failed",
                      error: result,
                    });
                  } else {
                    updateSubtask({
                      id: taskId,
                      status: "in_progress",
                    });
                  }
                }
              }
            }
            const results: React.ReactNode[] = [];
            for (const message of group.messages.filter(
              (message) => message.type === "ai",
            )) {
              if (hasReasoning(message)) {
                results.push(
                  <MessageGroup
                    key={"thinking-group-" + message.id}
                    messages={[message]}
                    isLoading={thread.isLoading}
                  />,
                );
              }
              results.push(
                <div
                  key="subtask-count"
                  className="text-muted-foreground pt-2 text-sm font-normal"
                >
                  {t.subtasks.executing(tasks.size)}
                </div>,
              );
              const taskIds = message.tool_calls
                ?.filter((toolCall) => toolCall.name === "task")
                .map((toolCall) => toolCall.id);
              for (const taskId of taskIds ?? []) {
                results.push(
                  <SubtaskCard
                    key={"task-group-" + taskId}
                    taskId={taskId!}
                    isLoading={thread.isLoading}
                  />,
                );
              }
            }
            return (
              <div
                key={"subtask-group-" + group.id}
                className="relative z-1 flex flex-col gap-2"
              >
                {results}
              </div>
            );
          }
          return (
            <MessageGroup
              key={"group-" + group.id}
              messages={group.messages}
              isLoading={thread.isLoading}
            />
          );
        })}
        {thread.isLoading && <StreamingIndicator className="my-4" />}
        <div style={{ height: `${paddingBottom}px` }} />
      </ConversationContent>
    </Conversation>
  );
}

function PlanReviewCard({
  todos,
  version,
  title,
  status,
  errorCode,
  errorMessage,
  onAction,
  onSave,
}: {
  todos: PlanReviewTodo[];
  version: number;
  title?: string;
  status: "pending_review" | "failed";
  errorCode?: string;
  errorMessage?: string;
  onAction?: (action: "confirm" | "retry", planVersion: number) => void;
  onSave?: (
    todos: PlanReviewTodo[],
    planVersion: number,
  ) => Promise<boolean> | boolean;
}) {
  const { t } = useI18n();
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState<PlanReviewTodo[]>(todos);
  const [error, setError] = useState<string>("");

  const normalizedTodos = useMemo(
    () => (isEditing ? draft : todos),
    [draft, isEditing, todos],
  );

  return (
    <div
      className="bg-background w-full rounded-lg border p-4"
      data-testid="plan-review-card"
    >
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-medium">
          {title?.trim() || t.planReview.title} · v{version}
        </div>
        {!isEditing ? (
          <div className="flex items-center gap-2">
            {status !== "failed" && (
              <Button
                size="sm"
                variant="default"
                onClick={() => onAction?.("confirm", version)}
                data-testid="plan-review-confirm"
              >
                {t.planReview.confirm}
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setDraft(todos);
                setError("");
                setIsEditing(true);
              }}
              data-testid="plan-review-edit"
            >
              {t.planReview.edit}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onAction?.("retry", version)}
              data-testid="plan-review-retry"
            >
              {t.planReview.retry}
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="default"
              onClick={async () => {
                if (draft.length === 0) {
                  setError(t.planReview.emptyError);
                  return;
                }
                if (draft.some((todo) => !todo.content.trim())) {
                  setError(t.planReview.blankError);
                  return;
                }
                const result = await onSave?.(
                  draft.map((todo) => ({ ...todo, content: todo.content.trim() })),
                  version,
                );
                if (result === false) {
                  return;
                }
                setError("");
                setIsEditing(false);
              }}
              data-testid="plan-review-save"
            >
              {t.planReview.save}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setDraft(todos);
                setError("");
                setIsEditing(false);
              }}
              data-testid="plan-review-cancel"
            >
              {t.planReview.cancel}
            </Button>
          </div>
        )}
      </div>

      {status === "failed" && (
        <div
          className="text-destructive mb-3 rounded border border-red-400/40 px-3 py-2 text-xs"
          data-testid="plan-review-failed-banner"
        >
          <div className="font-medium">{t.planReview.failedTitle}</div>
          {(errorMessage || errorCode) && (
            <div className="mt-1">
              {errorMessage || errorCode}
              {errorMessage && errorCode ? ` (${errorCode})` : ""}
            </div>
          )}
          <div className="mt-1 opacity-80">{t.planReview.failedRetryHint}</div>
        </div>
      )}

      <div className="space-y-2">
        {normalizedTodos.map((todo, idx) => (
          <div key={idx} className="flex items-start gap-2">
            <div className="text-muted-foreground mt-2 text-xs">{idx + 1}.</div>
            {isEditing ? (
              <Textarea
                className="min-h-10"
                value={todo.content}
                data-testid={`plan-review-input-${idx}`}
                onChange={(event) => {
                  const next = [...draft];
                  next[idx] = { ...next[idx], content: event.target.value };
                  setDraft(next);
                }}
              />
            ) : (
              <div className="text-sm" data-testid={`plan-review-item-${idx}`}>
                {todo.content}
              </div>
            )}
            {isEditing && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  const next = draft.filter((_, i) => i !== idx);
                  setDraft(next);
                }}
                data-testid={`plan-review-remove-${idx}`}
              >
                ×
              </Button>
            )}
          </div>
        ))}
      </div>

      {isEditing && (
        <div className="mt-3 flex items-center justify-between">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setDraft([...draft, { content: "" }])}
            data-testid="plan-review-add"
          >
            {t.planReview.addTodo}
          </Button>
          {error && <div className="text-destructive text-xs">{error}</div>}
        </div>
      )}
    </div>
  );
}
