import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useAgents } from "@/features/agents/hooks";
import { streamAgentChat } from "@/features/chat/api";
import { useChat } from "@/features/chat/hooks";
import type { ChatMessage as ApiChatMessage } from "@/features/chat/types";
import { useConversationDetail } from "@/features/conversations/hooks";
import { EmptyState } from "@/shared/components/feedback/EmptyState";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { createId } from "@/shared/lib/id";
import { ChatInput } from "@/pages/chat/components/ChatInput";
import { AgentSelector } from "@/pages/chat/components/AgentSelector";
import { MessageList } from "@/pages/chat/components/MessageList";
import { StreamMessage } from "@/pages/chat/components/StreamMessage";

const DEFAULT_AGENT_ID = "chat_agent";

type RenderMessage = {
  id: string;
  role: string;
  content: string;
};

function toRenderMessages(messages: ApiChatMessage[]): RenderMessage[] {
  return messages.map((message, index) => ({
    id: `${message.role}-${index}-${message.content.slice(0, 24) || createId("msg")}`,
    role: message.role,
    content: message.content,
  }));
}

function readRunId(metadata: Record<string, unknown>) {
  const runId = metadata.run_id;
  return typeof runId === "string" && runId.length > 0 ? runId : null;
}

function selectDefaultAgentId(agentIds: string[]) {
  if (agentIds.includes(DEFAULT_AGENT_ID)) {
    return DEFAULT_AGENT_ID;
  }
  return agentIds[0] ?? DEFAULT_AGENT_ID;
}

function buildSearchParams(agentId: string, conversationId?: string | null) {
  const params = new URLSearchParams();
  params.set("agentId", agentId);
  if (conversationId) {
    params.set("conversationId", conversationId);
  }
  return params;
}

export function ChatPage() {
  const chatMutation = useChat();
  const agentsQuery = useAgents();
  const [searchParams, setSearchParams] = useSearchParams();
  const resumeConversationId = searchParams.get("conversationId");
  const resumeAgentId = searchParams.get("agentId");
  const conversationQuery = useConversationDetail(resumeConversationId ?? "");
  const hydratedConversationIdRef = useRef<string | null>(null);

  const [draft, setDraft] = useState("");
  const [mode, setMode] = useState<"sync" | "stream">("sync");
  const [selectedAgentId, setSelectedAgentId] = useState(
    resumeAgentId ?? DEFAULT_AGENT_ID,
  );
  const [conversationId, setConversationId] = useState<string | null>(
    resumeConversationId,
  );
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ApiChatMessage[]>([]);
  const [streamContent, setStreamContent] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (resumeAgentId) {
      setSelectedAgentId(resumeAgentId);
      return;
    }

    const loadedAgents = agentsQuery.data ?? [];
    if (loadedAgents.length === 0) {
      return;
    }

    const loadedAgentIds = loadedAgents.map((agent) => agent.agentId);
    if (!loadedAgentIds.includes(selectedAgentId)) {
      setSelectedAgentId(selectDefaultAgentId(loadedAgentIds));
    }
  }, [agentsQuery.data, resumeAgentId, selectedAgentId]);

  useEffect(() => {
    if (!resumeConversationId) {
      hydratedConversationIdRef.current = null;
      return;
    }

    if (!conversationQuery.data) {
      return;
    }

    if (hydratedConversationIdRef.current === conversationQuery.data.id) {
      return;
    }

    hydratedConversationIdRef.current = conversationQuery.data.id;
    setConversationId(conversationQuery.data.id);
    setSelectedAgentId(conversationQuery.data.agentId ?? resumeAgentId ?? DEFAULT_AGENT_ID);
    setMessages(
      conversationQuery.data.messages.map((message) => ({
        role:
          message.role === "system" ||
          message.role === "assistant" ||
          message.role === "tool"
            ? message.role
            : "user",
        content: message.content,
        metadata: message.metadata,
      })),
    );
    setCurrentRunId(null);
    setStreamContent("");
    setErrorMessage(null);
  }, [conversationQuery.data, resumeAgentId, resumeConversationId]);

  function startFreshConversation(nextAgentId: string) {
    hydratedConversationIdRef.current = null;
    setSelectedAgentId(nextAgentId);
    setConversationId(null);
    setCurrentRunId(null);
    setMessages([]);
    setStreamContent("");
    setStreaming(false);
    setErrorMessage(null);
    setDraft("");
    setSearchParams(buildSearchParams(nextAgentId), { replace: true });
  }

  function rememberConversation(nextAgentId: string, nextConversationId: string | null) {
    setSearchParams(buildSearchParams(nextAgentId, nextConversationId), {
      replace: true,
    });
  }

  async function handleSyncSubmit() {
    const content = draft.trim();
    if (!content) {
      return;
    }

    const latestUserMessage: ApiChatMessage = {
      role: "user",
      content,
    };
    const nextMessages: ApiChatMessage[] = [
      ...messages,
      latestUserMessage,
    ];

    setErrorMessage(null);
    setStreamContent("");
    setCurrentRunId(null);
    setMessages(nextMessages);
    setDraft("");

    try {
      const response = await chatMutation.mutateAsync({
        agentId: selectedAgentId,
        payload: {
          messages: [latestUserMessage],
          conversationId: conversationId ?? undefined,
          taskType: selectedAgentId === "code_agent" ? "code_assist" : undefined,
        },
      });

      const nextConversationId = response.conversationId ?? conversationId;
      setMessages(response.messages.length > 0 ? response.messages : nextMessages);
      if (nextConversationId) {
        setConversationId(nextConversationId);
      }
      setCurrentRunId(readRunId(response.metadata));
      rememberConversation(selectedAgentId, nextConversationId);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "聊天请求失败");
    }
  }

  async function handleStreamSubmit() {
    const content = draft.trim();
    if (!content) {
      return;
    }

    const latestUserMessage: ApiChatMessage = {
      role: "user",
      content,
    };
    const nextMessages: ApiChatMessage[] = [
      ...messages,
      latestUserMessage,
    ];

    setErrorMessage(null);
    setStreamContent("");
    setCurrentRunId(null);
    setMessages(nextMessages);
    setDraft("");
    setStreaming(true);

    try {
      await streamAgentChat(
        {
          agentId: selectedAgentId,
          payload: {
            messages: [latestUserMessage],
            conversationId: conversationId ?? undefined,
            taskType: selectedAgentId === "code_agent" ? "code_assist" : undefined,
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
            rememberConversation(meta.agentId ?? selectedAgentId, nextConversationId);
          },
          onMessage: (contentChunk) => {
            setStreamContent(contentChunk);
          },
          onDone: (response) => {
            const nextConversationId = response.conversationId ?? conversationId;
            setMessages(
              response.messages.length > 0 ? response.messages : nextMessages,
            );
            if (nextConversationId) {
              setConversationId(nextConversationId);
            }
            setCurrentRunId(readRunId(response.metadata));
            setStreamContent("");
            rememberConversation(response.agentId ?? selectedAgentId, nextConversationId);
          },
          onError: (error) => {
            setErrorMessage(error.message);
            setStreamContent("");
          },
        },
      );
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "流式聊天请求失败",
      );
      setStreamContent("");
    } finally {
      setStreaming(false);
    }
  }

  const renderMessages = toRenderMessages(messages);
  const isSubmitting = chatMutation.isPending || streaming;

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-brand-700">
          Chat
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">
          Agent 对话工作台
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          支持两个独立智能体、历史会话继续对话，以及同步和流式两种交互模式。
        </p>
      </div>

      <AgentSelector
        agents={agentsQuery.data ?? []}
        selectedAgentId={selectedAgentId}
        disabled={isSubmitting}
        loading={agentsQuery.isLoading}
        errorMessage={agentsQuery.isError ? agentsQuery.error.message : null}
        onSelect={(agentId) => {
          if (agentId === selectedAgentId && !resumeConversationId) {
            return;
          }
          startFreshConversation(agentId);
        }}
      />

      {resumeConversationId && conversationQuery.isLoading ? (
        <Card>
          <p className="text-sm text-slate-500">正在加载历史会话内容...</p>
        </Card>
      ) : null}

      {resumeConversationId && conversationQuery.isError ? (
        <ErrorState message={conversationQuery.error.message} />
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <p className="text-sm text-slate-500">当前 Agent</p>
          <p className="mt-3 break-all text-lg font-semibold text-slate-900">
            {selectedAgentId}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">会话 ID</p>
          <p className="mt-3 break-all text-lg font-semibold text-slate-900">
            {conversationId ?? "尚未创建"}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">最近运行 ID</p>
          <p className="mt-3 break-all text-lg font-semibold text-slate-900">
            {currentRunId ?? "尚未返回"}
          </p>
        </Card>
      </div>

      {chatMutation.isError ? (
        <ErrorState message={chatMutation.error.message} />
      ) : null}

      {errorMessage && !chatMutation.isError ? (
        <ErrorState message={errorMessage} />
      ) : null}

      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            <Button
              variant={mode === "sync" ? "primary" : "secondary"}
              size="sm"
              onClick={() => {
                setMode("sync");
              }}
              disabled={isSubmitting}
            >
              非流式
            </Button>
            <Button
              variant={mode === "stream" ? "primary" : "secondary"}
              size="sm"
              onClick={() => {
                setMode("stream");
              }}
              disabled={isSubmitting}
            >
              流式
            </Button>
          </div>

          {conversationId ? (
            <Button
              variant="ghost"
              size="sm"
              disabled={isSubmitting}
              onClick={() => {
                startFreshConversation(selectedAgentId);
              }}
            >
              开启新会话
            </Button>
          ) : null}
        </div>

        {renderMessages.length === 0 ? (
          <EmptyState
            title="还没有对话消息"
            description="输入一条消息后，这里会展示当前智能体返回的完整消息历史。"
          />
        ) : (
          <ScrollArea className="max-h-[520px] pr-2">
            <MessageList messages={renderMessages} />
          </ScrollArea>
        )}

        <StreamMessage
          content={
            streaming
              ? streamContent || "等待流式响应中..."
              : mode === "stream"
                ? "流式模式下，发送后会在这里展示增量回复。"
                : "切换到流式模式后，这里会展示实时返回的内容。"
          }
          active={streaming}
        />
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
          disabled={conversationQuery.isLoading}
          isSubmitting={isSubmitting}
          submitLabel={mode === "stream" ? "流式发送" : "发送"}
        />
      </Card>
    </section>
  );
}
