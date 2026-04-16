import type { Message, Thread } from "@langchain/langgraph-sdk";

import type { Todo } from "../todos";

export interface PlanReviewTodo {
  content: string;
  status?: string;
}

export interface PlanReviewState {
  status:
    | "pending_review"
    | "approved"
    | "executing"
    | "completed"
    | "failed";
  version: number;
  todos: PlanReviewTodo[];
  updated_at: number;
  title?: string;
  error_code?: string;
  error_message?: string;
  consecutive_failures?: number;
  last_event_at?: number;
}

export interface AgentThreadState extends Record<string, unknown> {
  title: string;
  messages: Message[];
  artifacts: string[];
  todos?: Todo[];
  plan_review?: PlanReviewState;
}

export interface AgentThreadContext extends Record<string, unknown> {
  thread_id: string;
  model_name: string | undefined;
  thinking_enabled: boolean;
  is_plan_mode: boolean;
  subagent_enabled: boolean;
  reasoning_effort?: "minimal" | "low" | "medium" | "high";
  agent_name?: string;
}

export interface AgentThread extends Thread<AgentThreadState> {
  context?: AgentThreadContext;
}
