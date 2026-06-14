import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Bot } from "lucide-react";

import { cancelAgentRun } from "@/features/agent-runs/api";
import { useAgents } from "@/features/agents/hooks";
import {
  resumeChat,
  sendAgentChat,
  streamAgentChat,
  streamResumeChat,
} from "@/features/chat/api";
import type {
  ChatMessage as ApiChatMessage,
  ChatResponse,
  PendingHumanInput,
} from "@/features/chat/types";
import { useConversationDetail } from "@/features/conversations/hooks";
import type {
  ConversationDetail,
  ConversationLatestRun,
} from "@/features/conversations/types";
import { ChatInput } from "@/pages/chat/components/ChatInput";
import { HumanInputForm } from "@/pages/chat/components/HumanInputForm";
import { MessageList } from "@/pages/chat/components/MessageList";
import { AgentSelector } from "@/pages/chat/components/AgentSelector";
import {
  applyResumeMessageToResponse,
  buildResponseExecutionActivities,
  buildResumeMessage,
  buildRunningExecutionActivities,
  createLocalTimelineMessage,
  failStreamingAssistantMessage,
  mergeConversationHistoryWithTimeline,
  mergeTimelineWithResponse,
  type TimelineMessage,
  toRenderMessages,
  upsertStreamingAssistantMessage,
  upsertStreamingNodeActivity,
  upsertStreamingToolActivity,
} from "@/pages/chat/chatTimeline";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { QUERY_KEYS } from "@/shared/constants/query-keys";
import { createId } from "@/shared/lib/id";

const DEFAULT_AGENT_ID = "coordinator_agent";

function readRunId(metadata: Record<string, unknown>) {
  const runId = metadata.run_id;
  return typeof runId === "string" && runId.length > 0 ? runId : null;
}

function buildSearchParams(conversationId?: string | null) {
  const params = new URLSearchParams();
  if (conversationId) {
    params.set("conversationId", conversationId);
  }
  return params;
}

function findAgentLabel(
  agentId: string | null,
  agents: Array<{ agentId: string; name: string }>,
) {
  if (!agentId) {
    return "待路由";
  }
  const matched = agents.find((agent) => agent.agentId === agentId);
  return matched ? `${matched.name} (${matched.agentId})` : agentId;
}

function getPendingHumanInputFromRun(
  latestRun: ConversationLatestRun | null,
): PendingHumanInput | null {
  if (
    latestRun?.status !== "interrupted" ||
    latestRun.interruptSource !== "human_input" ||
    !latestRun.resumeAvailable
  ) {
    return null;
  }
  return latestRun.pendingHumanInput;
}

function buildConversationSnapshotKey(conversation: ConversationDetail) {
  return JSON.stringify({
    id: conversation.id,
    messages: conversation.messages.map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      metadata: message.metadata,
      createdAt: message.createdAt,
    })),
    latestRun: conversation.latestRun
      ? {
          id: conversation.latestRun.id,
          agentId: conversation.latestRun.agentId,
          status: conversation.latestRun.status,
          interruptSource: conversation.latestRun.interruptSource,
          resumeAvailable: conversation.latestRun.resumeAvailable,
          updatedAt: conversation.latestRun.updatedAt,
          pendingHumanInput: conversation.latestRun.pendingHumanInput,
        }
      : null,
    runTraces: conversation.runTraces,
  });
}

export function ChatPage() {
  const queryClient = useQueryClient();
  const agentsQuery = useAgents();
  const [searchParams, setSearchParams] = useSearchParams();
  const resumeConversationId = searchParams.get("conversationId");
  const conversationQuery = useConversationDetail(resumeConversationId ?? "");

  const [draft, setDraft] = useState("");
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [mode, setMode] = useState<"sync" | "stream">("stream");
  const [conversationId, setConversationId] = useState<string | null>(
    resumeConversationId,
  );
  const [hydratedConversationId, setHydratedConversationId] = useState<
    string | null
  >(null);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [messages, setMessages] = useState<TimelineMessage[]>([]);
  const [requestInFlight, setRequestInFlight] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [pendingHumanInput, setPendingHumanInput] =
    useState<PendingHumanInput | null>(null);
  const [activeAgentId, setActiveAgentId] =
    useState<string | null>(DEFAULT_AGENT_ID);
  const [routedAgentId, setRoutedAgentId] = useState<string | null>(null);
  const streamMessageIdRef = useRef<string | null>(null);
  const appliedConversationSnapshotKeyRef = useRef<string | null>(null);
  const messageViewportRef = useRef<HTMLDivElement | null>(null);

  const isHydratingConversation = Boolean(
    resumeConversationId &&
      hydratedConversationId !== resumeConversationId &&
      conversationQuery.isLoading,
  );
  const hasConversationLoadError = Boolean(
    resumeConversationId &&
      hydratedConversationId !== resumeConversationId &&
      conversationQuery.isError,
  );
  const renderMessages = toRenderMessages(messages);
  const isSubmitting = requestInFlight;
  const visibleAgentLabel = findAgentLabel(
    activeAgentId,
    agentsQuery.data ?? [],
  );
  const routedAgentLabel = findAgentLabel(
    routedAgentId,
    agentsQuery.data ?? [],
  );

  useEffect(() => {
    const conversation = conversationQuery.data;
    if (!resumeConversationId || !conversation) {
      return;
    }

    if (conversation.id !== resumeConversationId) {
      return;
    }

    if (requestInFlight && conversationId === conversation.id) {
      return;
    }

    const snapshotKey = buildConversationSnapshotKey(conversation);
    if (appliedConversationSnapshotKeyRef.current === snapshotKey) {
      return;
    }

    const latestRun = conversation.latestRun;
    appliedConversationSnapshotKeyRef.current = snapshotKey;
    setConversationId(conversation.id);
    setHydratedConversationId(conversation.id);
    setMessages((currentMessages) =>
      mergeConversationHistoryWithTimeline(
        conversation.messages,
        currentMessages,
        conversation.runTraces,
      ),
    );
    setCurrentRunId(latestRun?.id ?? null);
    setErrorMessage(null);
    setPendingHumanInput(getPendingHumanInputFromRun(latestRun));
    setActiveAgentId(
      conversation.agentId ?? DEFAULT_AGENT_ID,
    );
    setRoutedAgentId(
      latestRun?.agentId ?? conversation.agentId ?? null,
    );
  }, [
    conversationId,
    conversationQuery.data,
    requestInFlight,
    resumeConversationId,
  ]);

  useLayoutEffect(() => {
    const viewport = messageViewportRef.current;
    if (!viewport) {
      return;
    }
    viewport.scrollTop = viewport.scrollHeight;
  }, [messages]);

  function rememberConversation(nextConversationId: string | null) {
    setSearchParams(buildSearchParams(nextConversationId), {
      replace: true,
    });
  }

  function refreshConversationQueries(
    nextConversationId: string | null,
    runId: string | null,
  ) {
    void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.conversations });
    void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agentRuns });
    if (nextConversationId) {
      void queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.conversationDetail(nextConversationId),
      });
    }
    if (runId) {
      void queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.agentRunDetail(runId),
      });
    }
  }

  function startFreshConversation(agentId: string = DEFAULT_AGENT_ID) {
    streamMessageIdRef.current = null;
    appliedConversationSnapshotKeyRef.current = null;
    setConversationId(null);
    setHydratedConversationId(null);
    setCurrentRunId(null);
    setMessages([]);
    setRequestInFlight(false);
    setErrorMessage(null);
    setDraft("");
    setPendingHumanInput(null);
    setActiveAgentId(agentId);
    setRoutedAgentId(null);
    setSearchParams(buildSearchParams(), { replace: true });
  }

  function applyResponse(
    response: ChatResponse,
    fallbackMessages: TimelineMessage[] = [],
  ) {
    const nextConversationId = response.conversationId ?? conversationId;
    const nextRunId = readRunId(response.metadata);

    setMessages((currentMessages) =>
      mergeTimelineWithResponse(
        currentMessages.length > 0 ? currentMessages : fallbackMessages,
        response.messages,
        buildResponseExecutionActivities(response, activeAgentId),
      ),
    );
    if (nextConversationId) {
      setConversationId(nextConversationId);
      setHydratedConversationId(nextConversationId);
    }
    setCurrentRunId(nextRunId);
    setPendingHumanInput(response.pendingHumanInput);
    setRoutedAgentId(response.agentId ?? null);
    rememberConversation(nextConversationId);
    refreshConversationQueries(nextConversationId, nextRunId);
  }

  function appendLocalMessage(
    message: ApiChatMessage,
    fallbackPrefix: string,
  ): TimelineMessage {
    const timelineMessage = createLocalTimelineMessage(message, fallbackPrefix);
    setMessages((currentMessages) => [...currentMessages, timelineMessage]);
    return timelineMessage;
  }

  async function handleSyncSubmit() {
    if (requestInFlight) {
      return;
    }

    const content = draft.trim();
    if (!content) {
      return;
    }

    const latestUserMessage: ApiChatMessage = {
      role: "user",
      content,
    };
    const latestUserTimelineMessage = createLocalTimelineMessage(
      latestUserMessage,
      "user",
    );
    const fallbackMessages = [...messages, latestUserTimelineMessage];

    setErrorMessage(null);
    setCurrentRunId(null);
    setRequestInFlight(true);
    setMessages((currentMessages) => [
      ...currentMessages,
      latestUserTimelineMessage,
    ]);
    setDraft("");
    setPendingHumanInput(null);

    try {
      const response = await sendAgentChat({
        agentId: activeAgentId ?? DEFAULT_AGENT_ID,
        payload: {
          messages: [latestUserMessage],
          conversationId: conversationId ?? undefined,
        },
      });
      applyResponse(response, fallbackMessages);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "聊天请求失败");
    } finally {
      setRequestInFlight(false);
    }
  }

  async function handleStreamSubmit() {
    if (requestInFlight) {
      return;
    }

    const content = draft.trim();
    if (!content) {
      return;
    }

    const latestUserMessage: ApiChatMessage = {
      role: "user",
      content,
    };
    const latestUserTimelineMessage = createLocalTimelineMessage(
      latestUserMessage,
      "user",
    );
    const fallbackMessages = [...messages, latestUserTimelineMessage];
    const streamMessageId = createId("assistant-stream");
    const streamedMessageIds = new Map<string, string>();
    streamMessageIdRef.current = streamMessageId;

    setErrorMessage(null);
    setCurrentRunId(null);
    setMessages((currentMessages) => [
      ...currentMessages,
      latestUserTimelineMessage,
    ]);
    setDraft("");
    setRequestInFlight(true);
    setPendingHumanInput(null);

    try {
      await streamAgentChat(
        {
          agentId: activeAgentId ?? DEFAULT_AGENT_ID,
          payload: {
            messages: [latestUserMessage],
            conversationId: conversationId ?? undefined,
          },
        },
        {
          onStart: (meta) => {
            const nextConversationId = meta.conversationId ?? conversationId;
            if (nextConversationId) {
              setConversationId(nextConversationId);
            }
            if (meta.runId) {
              setCurrentRunId(meta.runId);
            }
            if (meta.agentId) {
              setRoutedAgentId(meta.agentId);
            }
            setMessages((currentMessages) =>
              upsertStreamingAssistantMessage(
                currentMessages,
                streamMessageId,
                "等待流式响应中...",
                buildRunningExecutionActivities(meta, activeAgentId),
              ),
            );
          },
          onMessage: (message) => {
            let timelineMessageId = streamedMessageIds.get(message.messageId);
            if (!timelineMessageId) {
              timelineMessageId =
                streamedMessageIds.size === 0
                  ? streamMessageId
                  : `${streamMessageId}-${message.messageId}`;
              streamedMessageIds.set(message.messageId, timelineMessageId);
            }
            setMessages((currentMessages) =>
              upsertStreamingAssistantMessage(
                currentMessages,
                timelineMessageId,
                message.content || "等待流式响应中...",
              ),
            );
          },
          onNode: (event) => {
            setMessages((currentMessages) =>
              upsertStreamingNodeActivity(
                currentMessages,
                streamMessageId,
                event,
              ),
            );
          },
          onTool: (event) => {
            setMessages((currentMessages) =>
              upsertStreamingToolActivity(
                currentMessages,
                streamMessageId,
                event,
              ),
            );
          },
          onInterrupt: (payload) => {
            const nextConversationId = payload.conversationId ?? conversationId;
            if (nextConversationId) {
              setConversationId(nextConversationId);
              rememberConversation(nextConversationId);
            }
            if (payload.runId) {
              setCurrentRunId(payload.runId);
            }
            setPendingHumanInput(payload.pendingHumanInput);
            if (payload.agentId) {
              setRoutedAgentId(payload.agentId);
            }
            refreshConversationQueries(
              nextConversationId,
              payload.runId ?? currentRunId,
            );
          },
          onDone: (response) => {
            streamMessageIdRef.current = null;
            applyResponse(response, fallbackMessages);
          },
          onError: (error) => {
            setErrorMessage(error.message);
            setMessages((currentMessages) =>
              failStreamingAssistantMessage(currentMessages, streamMessageId),
            );
          },
        },
      );
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "流式聊天请求失败",
      );
      setMessages((currentMessages) =>
        failStreamingAssistantMessage(currentMessages, streamMessageId),
      );
    } finally {
      setRequestInFlight(false);
      if (streamMessageIdRef.current === streamMessageId) {
        streamMessageIdRef.current = null;
      }
    }
  }

  async function handleResumeSync(input: Record<string, string>) {
    if (requestInFlight) {
      return;
    }

    if (!currentRunId) {
      setErrorMessage("当前缺少可恢复的运行 ID。");
      return;
    }

    const resumeMessage = buildResumeMessage(input, pendingHumanInput);
    const resumeTimelineMessage = resumeMessage
      ? appendLocalMessage(resumeMessage, "resume")
      : null;
    const fallbackMessages = resumeTimelineMessage
      ? [...messages, resumeTimelineMessage]
      : messages;

    setErrorMessage(null);
    setRequestInFlight(true);
    setPendingHumanInput(null);

    try {
      const response = await resumeChat({
        runId: currentRunId,
        input,
      });
      applyResponse(
        applyResumeMessageToResponse(response, resumeMessage),
        fallbackMessages,
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "恢复聊天失败");
    } finally {
      setRequestInFlight(false);
    }
  }

  async function handleResumeStream(input: Record<string, string>) {
    if (requestInFlight) {
      return;
    }

    if (!currentRunId) {
      setErrorMessage("当前缺少可恢复的运行 ID。");
      return;
    }

    const resumeMessage = buildResumeMessage(input, pendingHumanInput);
    const resumeTimelineMessage = resumeMessage
      ? appendLocalMessage(resumeMessage, "resume")
      : null;
    const fallbackMessages = resumeTimelineMessage
      ? [...messages, resumeTimelineMessage]
      : messages;
    const streamMessageId = createId("assistant-stream");
    const streamedMessageIds = new Map<string, string>();
    streamMessageIdRef.current = streamMessageId;

    setErrorMessage(null);
    setRequestInFlight(true);
    setPendingHumanInput(null);

    try {
      await streamResumeChat(
        {
          runId: currentRunId,
          input,
        },
        {
          onStart: (meta) => {
            if (meta.runId) {
              setCurrentRunId(meta.runId);
            }
            setMessages((currentMessages) =>
              upsertStreamingAssistantMessage(
                currentMessages,
                streamMessageId,
                "等待流式响应中...",
                buildRunningExecutionActivities(meta, activeAgentId),
              ),
            );
          },
          onMessage: (message) => {
            let timelineMessageId = streamedMessageIds.get(message.messageId);
            if (!timelineMessageId) {
              timelineMessageId =
                streamedMessageIds.size === 0
                  ? streamMessageId
                  : `${streamMessageId}-${message.messageId}`;
              streamedMessageIds.set(message.messageId, timelineMessageId);
            }
            setMessages((currentMessages) =>
              upsertStreamingAssistantMessage(
                currentMessages,
                timelineMessageId,
                message.content || "等待流式响应中...",
              ),
            );
          },
          onNode: (event) => {
            setMessages((currentMessages) =>
              upsertStreamingNodeActivity(
                currentMessages,
                streamMessageId,
                event,
              ),
            );
          },
          onTool: (event) => {
            setMessages((currentMessages) =>
              upsertStreamingToolActivity(
                currentMessages,
                streamMessageId,
                event,
              ),
            );
          },
          onInterrupt: (payload) => {
            const nextConversationId = payload.conversationId ?? conversationId;
            if (nextConversationId) {
              setConversationId(nextConversationId);
              rememberConversation(nextConversationId);
            }
            if (payload.runId) {
              setCurrentRunId(payload.runId);
            }
            setPendingHumanInput(payload.pendingHumanInput);
            if (payload.agentId) {
              setRoutedAgentId(payload.agentId);
            }
            refreshConversationQueries(
              nextConversationId,
              payload.runId ?? currentRunId,
            );
          },
          onDone: (response) => {
            streamMessageIdRef.current = null;
            applyResponse(
              applyResumeMessageToResponse(response, resumeMessage),
              fallbackMessages,
            );
          },
          onError: (error) => {
            setErrorMessage(error.message);
            setMessages((currentMessages) =>
              failStreamingAssistantMessage(currentMessages, streamMessageId),
            );
          },
        },
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "恢复聊天失败");
      setMessages((currentMessages) =>
        failStreamingAssistantMessage(currentMessages, streamMessageId),
      );
    } finally {
      setRequestInFlight(false);
      if (streamMessageIdRef.current === streamMessageId) {
        streamMessageIdRef.current = null;
      }
    }
  }

  async function handleCancelPendingRun() {
    if (!currentRunId) {
      return;
    }

    setErrorMessage(null);
    try {
      await cancelAgentRun(currentRunId, activeAgentId, "用户取消本次路线规划");
      setPendingHumanInput(null);
      refreshConversationQueries(conversationId, currentRunId);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "取消运行失败");
    }
  }

  return (
    <section className="h-full overflow-hidden flex flex-col gap-4 animate-fade-in">
      {/* 极简按钮控制行 */}
      <div className="flex items-center justify-between select-none shrink-0">
        <div className="flex items-center gap-2">
          {pendingHumanInput ? (
            <Badge variant="warning" className="text-[10px] px-2 py-0.5 animate-pulse">等待补参</Badge>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {conversationId ? (
            <Button
              variant="ghost"
              size="sm"
              disabled={isSubmitting}
              onClick={() => {
                startFreshConversation();
              }}
              className="text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 gap-1.5 h-8 rounded-xl"
            >
              新会话
            </Button>
          ) : null}
          <Button
            variant={showDebugPanel ? "primary" : "secondary"}
            size="sm"
            onClick={() => setShowDebugPanel(!showDebugPanel)}
            className="text-xs gap-1.5 h-8 rounded-xl shadow-sm"
          >
            🛠️ 运行诊断
          </Button>
        </div>
      </div>

      {isHydratingConversation ? (
        <Card className="flex items-center justify-center p-6 shrink-0">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-500"></span>
            </span>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">正在加载历史会话内容...</p>
          </div>
        </Card>
      ) : null}

      {hasConversationLoadError ? (
        <div className="shrink-0">
          <ErrorState
            message={conversationQuery.error?.message ?? "历史会话加载失败"}
          />
        </div>
      ) : null}

      {agentsQuery.isError ? (
        <Card className="border-amber-200 bg-amber-50/50 dark:border-amber-900/30 dark:bg-amber-950/20 p-4 shrink-0">
          <p className="text-sm text-amber-800 dark:text-amber-400 font-medium">
            智能体元信息加载失败，已自动回退到默认协调入口。
          </p>
        </Card>
      ) : null}

      {errorMessage ? (
        <div className="shrink-0">
          <ErrorState message={errorMessage} />
        </div>
      ) : null}

      {/* 主工作区 */}
      <div className="flex-1 min-h-0 flex gap-6 relative overflow-hidden">
        {/* 左侧对话交互区 */}
        <div className="flex-1 min-h-0 flex flex-col justify-between bg-transparent">
          {/* 对话消息滚动展示区 */}
          <div className="flex-1 min-h-0 flex flex-col">
            {renderMessages.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center select-none text-center px-4 animate-fade-in">
                <div className="space-y-4 max-w-lg">
                  <div className="inline-flex p-3.5 bg-gradient-to-tr from-[#4285f4] via-[#9b51e0] to-[#e040fb] rounded-full text-white shadow-md shadow-purple-500/10 animate-pulse">
                    <Bot size={32} />
                  </div>
                  <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-[#4285f4] via-[#9b51e0] to-[#e040fb] dark:from-[#a8c7fa] dark:via-[#d7aefb] dark:to-[#ffb2ff] bg-clip-text text-transparent font-display">
                    今天想聊点什么？
                  </h1>
                  <p className="text-sm text-slate-400 dark:text-slate-500 leading-relaxed">
                    多智能体协作网络。输入问题开启对话，系统会自动完成意图识别、路线规划与多 Agent 协作链派发。
                  </p>
                </div>
              </div>
            ) : (
              <ScrollArea
                ref={messageViewportRef}
                className="flex-1 min-h-0 w-full"
              >
                <div className="w-full px-6 py-2">
                  <MessageList messages={renderMessages} />
                </div>
              </ScrollArea>
            )}
          </div>

          {/* 输入框区 */}
          <div className="shrink-0 w-full pt-4 pb-2">
            <div className="w-full px-6">
              {pendingHumanInput ? (
                <HumanInputForm
                  pendingHumanInput={pendingHumanInput}
                  disabled={isHydratingConversation}
                  isSubmitting={isSubmitting}
                  onCancel={() => {
                    void handleCancelPendingRun();
                  }}
                  onSubmit={(input) => {
                    if (mode === "stream") {
                      void handleResumeStream(input);
                      return;
                    }
                    void handleResumeSync(input);
                  }}
                />
              ) : (
                <ChatInput
                  value={draft}
                  onChange={setDraft}
                  onSubmit={() => {
                    if (mode === "stream") {
                      void handleStreamSubmit();
                      return;
                    }
                    void handleSyncSubmit();
                  }}
                  disabled={isHydratingConversation}
                  isSubmitting={isSubmitting}
                  submitLabel={mode === "stream" ? "流式发送" : "发送"}
                />
              )}
            </div>
          </div>
        </div>

        {/* 右侧折叠调试抽屉 */}
        <div
          className={`shrink-0 h-full flex flex-col border-l border-slate-200/80 dark:border-slate-800/80 bg-white/80 dark:bg-slate-900/60 backdrop-blur-md transition-all duration-300 overflow-hidden ${
            showDebugPanel ? "w-[360px] p-5 border-l" : "w-0 p-0 border-l-transparent"
          }`}
        >
          <div className="flex-1 min-h-0 overflow-y-auto space-y-5 pr-1">
            {/* 调试控制台 Header */}
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/50 pb-3 select-none">
              <div>
                <p className="text-sm font-bold text-slate-900 dark:text-slate-100 font-display">调试与路由诊断</p>
                <p className="text-[10px] text-slate-400 dark:text-slate-500">
                  供开发调试使用，正常对话建议收起。
                </p>
              </div>
              
              {/* 会话模式切换 */}
              <div className="flex items-center bg-slate-100/60 dark:bg-slate-955/40 p-0.5 rounded-xl border border-slate-200/50 dark:border-slate-800/40 select-none">
                <Button
                  variant={mode === "sync" ? "primary" : "ghost"}
                  size="sm"
                  onClick={() => {
                    setMode("sync");
                  }}
                  disabled={isSubmitting}
                  className="text-[10px] px-2 py-0.5 h-6 rounded-lg"
                >
                  同步
                </Button>
                <Button
                  variant={mode === "stream" ? "primary" : "ghost"}
                  size="sm"
                  onClick={() => {
                    setMode("stream");
                  }}
                  disabled={isSubmitting}
                  className="text-[10px] px-2 py-0.5 h-6 rounded-lg"
                >
                  流式
                </Button>
              </div>
            </div>

            {/* 系统配置参数 */}
            <div className="space-y-3 p-1">
              <div>
                <p className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">系统配置信息</p>
              </div>

              <div className="grid gap-2 font-mono text-[11px]">
                <div className="flex items-center justify-between rounded-xl border border-slate-200/50 bg-slate-50/30 px-3 py-2 dark:border-slate-800/50 dark:bg-slate-950/15">
                  <span className="text-[10px] text-slate-400 dark:text-slate-500 uppercase font-semibold">默认入口</span>
                  <span className="break-all text-xs font-bold text-slate-800 dark:text-slate-200 font-mono">
                    {DEFAULT_AGENT_ID}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-slate-200/50 bg-slate-50/30 px-3 py-2 dark:border-slate-800/50 dark:bg-slate-950/15">
                  <span className="text-[10px] text-slate-400 dark:text-slate-500 uppercase font-semibold">接口目标</span>
                  <span className="break-all text-xs font-bold text-slate-800 dark:text-slate-200 font-mono">
                    {visibleAgentLabel}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-slate-200/50 bg-slate-50/30 px-3 py-2 dark:border-slate-800/50 dark:bg-slate-950/15">
                  <span className="text-[10px] text-slate-400 dark:text-slate-500 uppercase font-semibold">已路由到</span>
                  <span className="break-all text-xs font-bold text-slate-800 dark:text-slate-200 font-mono">
                    {routedAgentLabel}
                  </span>
                </div>
                <div className="rounded-xl border border-slate-200/50 bg-slate-50/30 p-2.5 dark:border-slate-800/50 dark:bg-slate-950/15">
                  <p className="text-[10px] text-slate-400 dark:text-slate-500 uppercase font-semibold">当前会话 ID</p>
                  <p className="mt-0.5 break-all text-[10px] font-bold text-slate-600 dark:text-slate-400 font-mono">
                    {conversationId ?? "尚未创建"}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200/50 bg-slate-50/30 p-2.5 dark:border-slate-800/50 dark:bg-slate-950/15">
                  <p className="text-[10px] text-slate-400 dark:text-slate-500 uppercase font-semibold">最近运行 ID</p>
                  <p className="mt-0.5 break-all text-[10px] font-bold text-slate-600 dark:text-slate-450 font-mono">
                    {currentRunId ?? "尚未返回"}
                  </p>
                </div>
              </div>
            </div>

            {/* 智能体选择 */}
            <AgentSelector
              agents={agentsQuery.data ?? []}
              selectedAgentId={activeAgentId ?? DEFAULT_AGENT_ID}
              disabled={isSubmitting}
              loading={agentsQuery.isLoading}
              errorMessage={agentsQuery.isError ? "加载可用智能体元数据失败" : null}
              onSelect={(agentId) => startFreshConversation(agentId)}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
