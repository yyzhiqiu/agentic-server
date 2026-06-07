import { useNavigate, useParams } from "react-router-dom";

import { useConversationDetail } from "@/features/conversations/hooks";
import { EmptyState } from "@/shared/components/feedback/EmptyState";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { LoadingState } from "@/shared/components/feedback/LoadingState";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { Separator } from "@/shared/components/ui/separator";
import { GUEST_USER_LABEL } from "@/shared/constants/app";
import { ROUTES } from "@/shared/constants/routes";
import { formatDate } from "@/shared/lib/date";
import { MessageList } from "@/pages/chat/components/MessageList";

function buildContinueUrl(conversationId: string, agentId: string | null) {
  const params = new URLSearchParams();
  params.set("conversationId", conversationId);
  params.set("agentId", agentId ?? "chat_agent");
  return `${ROUTES.chat}?${params.toString()}`;
}

export function ConversationDetailPage() {
  const navigate = useNavigate();
  const { conversationId } = useParams();
  const conversationQuery = useConversationDetail(conversationId ?? "");
  const messages = (conversationQuery.data?.messages ?? []).map((message) => ({
    id: message.id,
    role: message.role,
    content: message.content,
  }));

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-brand-700">
          Conversation Detail
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">会话详情</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          这里展示会话元信息、绑定智能体和已持久化消息，并支持直接回到聊天页继续对话。
        </p>
      </div>

      {!conversationId ? (
        <ErrorState message="缺少会话 ID，无法加载详情。" />
      ) : null}

      {conversationId && conversationQuery.isLoading ? (
        <LoadingState title="正在加载会话详情..." />
      ) : null}

      {conversationId && conversationQuery.isError ? (
        <ErrorState message={conversationQuery.error.message} />
      ) : null}

      {conversationId &&
      !conversationQuery.isLoading &&
      !conversationQuery.isError &&
      conversationQuery.data ? (
        <>
          <Card className="space-y-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  {conversationQuery.data.title ?? "未命名会话"}
                </h2>
                <p className="mt-2 break-all text-sm text-slate-500">
                  会话 ID: {conversationQuery.data.id}
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => {
                  navigate(
                    buildContinueUrl(
                      conversationQuery.data.id,
                      conversationQuery.data.agentId,
                    ),
                  );
                }}
              >
                继续对话
              </Button>
            </div>

            <Separator />

            <div className="grid gap-3 text-sm text-slate-600 md:grid-cols-4">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  用户
                </p>
                <p className="mt-1 break-all text-slate-700">
                  {conversationQuery.data.userId ?? GUEST_USER_LABEL}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  Agent
                </p>
                <p className="mt-1 text-slate-700">
                  {conversationQuery.data.agentId ?? "chat_agent"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  创建时间
                </p>
                <p className="mt-1 text-slate-700">
                  {conversationQuery.data.createdAt
                    ? formatDate(conversationQuery.data.createdAt)
                    : "暂无"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  消息数量
                </p>
                <p className="mt-1 text-slate-700">{messages.length}</p>
              </div>
            </div>
          </Card>

          {messages.length === 0 ? (
            <EmptyState
              title="这个会话还没有持久化消息"
              description="这个会话暂时没有消息记录。新消息写入后，这里会直接展示完整消息历史。"
            />
          ) : (
            <Card className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">消息历史</h2>
                <p className="mt-1 text-sm text-slate-500">
                  这里展示的是后端已持久化的消息列表。
                </p>
              </div>
              <ScrollArea className="max-h-[520px] pr-2">
                <MessageList messages={messages} />
              </ScrollArea>
            </Card>
          )}
        </>
      ) : null}
    </section>
  );
}
