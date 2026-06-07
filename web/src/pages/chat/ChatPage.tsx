import { useState } from "react";

import { streamChat } from "@/features/chat/api";
import { useChat } from "@/features/chat/hooks";
import type { ChatMessage as ApiChatMessage } from "@/features/chat/types";
import { EmptyState } from "@/shared/components/feedback/EmptyState";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { Button } from "@/shared/components/ui/button";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { MessageList } from "@/pages/chat/components/MessageList";
import { ChatInput } from "@/pages/chat/components/ChatInput";
import { StreamMessage } from "@/pages/chat/components/StreamMessage";
import { Card } from "@/shared/components/ui/card";
import { createId } from "@/shared/lib/id";

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

export function ChatPage() {
  const chatMutation = useChat();
  const [draft, setDraft] = useState("");
  const [mode, setMode] = useState<"sync" | "stream">("sync");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ApiChatMessage[]>([]);
  const [streamContent, setStreamContent] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSyncSubmit() {
    const content = draft.trim();
    if (!content) {
      return;
    }

    const nextMessages: ApiChatMessage[] = [
      ...messages,
      {
        role: "user",
        content,
      },
    ];

    setErrorMessage(null);
    setStreamContent("");
    setCurrentRunId(null);
    setMessages(nextMessages);
    setDraft("");

    try {
      const response = await chatMutation.mutateAsync({
        messages: nextMessages,
        conversationId: conversationId ?? undefined,
      });

      setMessages(response.messages.length > 0 ? response.messages : nextMessages);
      if (response.conversationId) {
        setConversationId(response.conversationId);
      }
      setCurrentRunId(readRunId(response.metadata));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "聊天请求失败");
    }
  }

  async function handleStreamSubmit() {
    const content = draft.trim();
    if (!content) {
      return;
    }

    const nextMessages: ApiChatMessage[] = [
      ...messages,
      {
        role: "user",
        content,
      },
    ];

    setErrorMessage(null);
    setStreamContent("");
    setCurrentRunId(null);
    setMessages(nextMessages);
    setDraft("");
    setStreaming(true);

    try {
      await streamChat(
        {
          messages: nextMessages,
          conversationId: conversationId ?? undefined,
        },
        {
          onStart: (meta) => {
            if (meta.conversationId) {
              setConversationId(meta.conversationId);
            }
            if (meta.runId) {
              setCurrentRunId(meta.runId);
            }
          },
          onMessage: (contentChunk) => {
            setStreamContent(contentChunk);
          },
          onDone: (response) => {
            setMessages(
              response.messages.length > 0 ? response.messages : nextMessages,
            );
            if (response.conversationId) {
              setConversationId(response.conversationId);
            }
            setCurrentRunId(readRunId(response.metadata));
            setStreamContent("");
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
          支持同步对话与流式响应两种模式，可在消息区查看回复内容、会话标识与最近一次运行信息。
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
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

        {renderMessages.length === 0 ? (
          <EmptyState
            title="还没有对话消息"
            description="输入一条消息后，这里会展示返回的消息历史。"
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
          disabled={false}
          isSubmitting={isSubmitting}
          submitLabel={mode === "stream" ? "流式发送" : "发送"}
        />
      </Card>
    </section>
  );
}
