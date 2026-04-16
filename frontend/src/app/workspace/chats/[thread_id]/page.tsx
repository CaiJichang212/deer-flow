"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { type PromptInputMessage } from "@/components/ai-elements/prompt-input";
import { ArtifactTrigger } from "@/components/workspace/artifacts";
import {
  ChatBox,
  useSpecificChatMode,
  useThreadChat,
} from "@/components/workspace/chats";
import { ExportTrigger } from "@/components/workspace/export-trigger";
import { InputBox } from "@/components/workspace/input-box";
import {
  MessageList,
  MESSAGE_LIST_DEFAULT_PADDING_BOTTOM,
  MESSAGE_LIST_FOLLOWUPS_EXTRA_PADDING_BOTTOM,
} from "@/components/workspace/messages";
import { ThreadContext } from "@/components/workspace/messages/context";
import { ThreadTitle } from "@/components/workspace/thread-title";
import { TodoList } from "@/components/workspace/todo-list";
import { TokenUsageIndicator } from "@/components/workspace/token-usage-indicator";
import { Welcome } from "@/components/workspace/welcome";
import { useI18n } from "@/core/i18n/hooks";
import { useNotification } from "@/core/notification/hooks";
import { useThreadSettings } from "@/core/settings";
import { getAPIClient } from "@/core/api";
import { getBackendBaseURL } from "@/core/config";
import { useThreadStream } from "@/core/threads/hooks";
import type { PlanReviewState } from "@/core/threads";
import type { PlanReviewTodo } from "@/core/threads";
import { textOfMessage } from "@/core/threads/utils";
import { env } from "@/env";
import { cn } from "@/lib/utils";

export default function ChatPage() {
  const { t } = useI18n();
  const [showFollowups, setShowFollowups] = useState(false);
  const { threadId, setThreadId, isNewThread, setIsNewThread, isMock } =
    useThreadChat();
  const [settings, setSettings] = useThreadSettings(threadId);
  const [mounted, setMounted] = useState(false);
  const [planReviewOverride, setPlanReviewOverride] =
    useState<PlanReviewState | null>(null);
  const [todosOverride, setTodosOverride] = useState<PlanReviewTodo[] | null>(
    null,
  );
  const lastPlanErrorRef = useRef<string>("");
  useSpecificChatMode();

  useEffect(() => {
    setMounted(true);
  }, []);

  const { showNotification } = useNotification();

  const [thread, sendMessage, isUploading] = useThreadStream({
    threadId: isNewThread ? undefined : threadId,
    context: settings.context,
    isMock,
    onStart: (createdThreadId) => {
      setThreadId(createdThreadId);
      setIsNewThread(false);
      // ! Important: Never use next.js router for navigation in this case, otherwise it will cause the thread to re-mount and lose all states. Use native history API instead.
      history.replaceState(null, "", `/workspace/chats/${createdThreadId}`);
    },
    onFinish: (state) => {
      if (document.hidden || !document.hasFocus()) {
        let body = "Conversation finished";
        const lastMessage = state.messages.at(-1);
        if (lastMessage) {
          const textContent = textOfMessage(lastMessage);
          if (textContent) {
            body =
              textContent.length > 200
                ? textContent.substring(0, 200) + "..."
                : textContent;
          }
        }
        showNotification(state.title, { body });
      }
    },
  });

  useEffect(() => {
    const remotePlanReview = thread.values.plan_review;
    if (
      planReviewOverride &&
      remotePlanReview &&
      (remotePlanReview.status === "failed" ||
        remotePlanReview.status === "completed" ||
        remotePlanReview.version >= planReviewOverride.version)
    ) {
      setPlanReviewOverride(null);
    }
  }, [planReviewOverride, thread.values.plan_review]);

  useEffect(() => {
    if (!todosOverride) {
      return;
    }
    const remoteTodos = thread.values.todos ?? [];
    if (JSON.stringify(remoteTodos) === JSON.stringify(todosOverride)) {
      setTodosOverride(null);
    }
  }, [todosOverride, thread.values.todos]);

  const effectivePlanReview = planReviewOverride ?? thread.values.plan_review;
  useEffect(() => {
    if (effectivePlanReview?.status !== "failed") {
      return;
    }
    const msg = (effectivePlanReview.error_message || "").trim();
    if (!msg || msg === lastPlanErrorRef.current) {
      return;
    }
    lastPlanErrorRef.current = msg;
    toast.error(msg);
  }, [effectivePlanReview]);
  const effectiveTodos = useMemo(() => {
    const source = todosOverride ?? (thread.values.todos ?? []);
    return source.map((todo) => {
      const status = todo.status;
      if (
        status === "pending" ||
        status === "in_progress" ||
        status === "completed" ||
        status === undefined
      ) {
        return { ...todo, status };
      }
      return { ...todo, status: "pending" as const };
    });
  }, [todosOverride, thread.values.todos]);

  const handleSubmit = useCallback(
    (message: PromptInputMessage) => {
      void sendMessage(threadId, message);
    },
    [sendMessage, threadId],
  );
  const handleStop = useCallback(async () => {
    await thread.stop();
  }, [thread]);

  const handlePlanAction = useCallback(
    (action: "confirm" | "retry", planVersion: number) => {
      const planReview = planReviewOverride ?? thread.values.plan_review;
      const nextAction =
        planReview?.status === "failed" ? "retry" : action;
      setPlanReviewOverride(null);
      void sendMessage(
        threadId,
        { text: "", files: [] },
        undefined,
        {
          additionalKwargs: {
            hide_from_ui: true,
            plan_action: nextAction,
            plan_version: planVersion,
          },
        },
      );
    },
    [planReviewOverride, sendMessage, thread.values.plan_review, threadId],
  );

  const handlePlanSave = useCallback(
    async (todos: PlanReviewTodo[], planVersion: number) => {
      const planReview = planReviewOverride ?? thread.values.plan_review;
      if (!planReview) {
        toast.error("保存计划失败");
        return false;
      }
      const nextPlanReview = {
        ...planReview,
        todos,
        status: "pending_review" as const,
        version: Math.max(planVersion + 1, (planReview.version ?? 0) + 1),
        updated_at: Math.floor(Date.now() / 1000),
      };
      try {
        const response = await fetch(
          `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/state`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              values: {
                plan_review: nextPlanReview,
                todos,
              },
            }),
          },
        );
        if (!response.ok) {
          throw new Error("request_failed");
        }
        setPlanReviewOverride(nextPlanReview);
        setTodosOverride(todos);
        return true;
      } catch {
        try {
          await getAPIClient(isMock).threads.updateState(threadId, {
            values: {
              plan_review: nextPlanReview,
              todos,
            },
          });
          setPlanReviewOverride(nextPlanReview);
          setTodosOverride(todos);
          return true;
        } catch {
          toast.error("保存计划失败");
          return false;
        }
      }
    },
    [isMock, planReviewOverride, thread.values.plan_review, threadId],
  );

  const messageListPaddingBottom = showFollowups
    ? MESSAGE_LIST_DEFAULT_PADDING_BOTTOM +
      MESSAGE_LIST_FOLLOWUPS_EXTRA_PADDING_BOTTOM
    : undefined;

  return (
    <ThreadContext.Provider value={{ thread, isMock }}>
      <ChatBox threadId={threadId}>
        <div className="relative flex size-full min-h-0 justify-between">
          <header
            className={cn(
              "absolute top-0 right-0 left-0 z-30 flex h-12 shrink-0 items-center px-4",
              isNewThread
                ? "bg-background/0 backdrop-blur-none"
                : "bg-background/80 shadow-xs backdrop-blur",
            )}
          >
            <div className="flex w-full items-center text-sm font-medium">
              <ThreadTitle threadId={threadId} thread={thread} />
            </div>
            <div className="flex items-center gap-2">
              <TokenUsageIndicator messages={thread.messages} />
              <ExportTrigger threadId={threadId} />
              <ArtifactTrigger />
            </div>
          </header>
          <main className="flex min-h-0 max-w-full grow flex-col">
            <div className="flex size-full justify-center">
              <MessageList
                className={cn("size-full", !isNewThread && "pt-10")}
                threadId={threadId}
                thread={thread}
                paddingBottom={messageListPaddingBottom}
                onPlanAction={handlePlanAction}
                onPlanSave={handlePlanSave}
                planReviewOverride={effectivePlanReview}
              />
            </div>
            <div className="absolute right-0 bottom-0 left-0 z-30 flex justify-center px-4">
              <div
                className={cn(
                  "relative w-full",
                  isNewThread && "-translate-y-[calc(50vh-96px)]",
                  isNewThread
                    ? "max-w-(--container-width-sm)"
                    : "max-w-(--container-width-md)",
                )}
              >
                <div className="absolute -top-4 right-0 left-0 z-0">
                  <div className="absolute right-0 bottom-0 left-0">
                    <TodoList
                      className="bg-background/5"
                      todos={effectiveTodos}
                      hidden={effectiveTodos.length === 0}
                    />
                  </div>
                </div>
                {mounted ? (
                  <InputBox
                    className={cn("bg-background/5 w-full -translate-y-4")}
                    isNewThread={isNewThread}
                    threadId={threadId}
                    autoFocus={isNewThread}
                    status={
                      thread.error
                        ? "error"
                        : thread.isLoading
                          ? "streaming"
                          : "ready"
                    }
                    context={settings.context}
                    extraHeader={
                      isNewThread && <Welcome mode={settings.context.mode} />
                    }
                    disabled={
                      env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" ||
                      isUploading
                    }
                    onContextChange={(context) =>
                      setSettings("context", context)
                    }
                    onFollowupsVisibilityChange={setShowFollowups}
                    onSubmit={handleSubmit}
                    onStop={handleStop}
                  />
                ) : (
                  <div
                    aria-hidden="true"
                    className={cn(
                      "bg-background/5 h-32 w-full -translate-y-4 rounded-2xl border",
                    )}
                  />
                )}
                {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" && (
                  <div className="text-muted-foreground/67 w-full translate-y-12 text-center text-xs">
                    {t.common.notAvailableInDemoMode}
                  </div>
                )}
              </div>
            </div>
          </main>
        </div>
      </ChatBox>
    </ThreadContext.Provider>
  );
}
