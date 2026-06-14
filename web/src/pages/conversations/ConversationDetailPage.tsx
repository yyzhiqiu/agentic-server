import { useNavigate, useParams } from "react-router-dom";

import { useConversationDetail } from "@/features/conversations/hooks";
import { EmptyState } from "@/shared/components/feedback/EmptyState";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { GUEST_USER_LABEL } from "@/shared/constants/app";
import { ROUTES } from "@/shared/constants/routes";
import { formatDate } from "@/shared/lib/date";
import { MessageList } from "@/pages/chat/components/MessageList";

function buildContinueUrl(conversationId: string) {
  const params = new URLSearchParams();
  params.set("conversationId", conversationId);
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
    <section className="h-full overflow-y-auto pr-2 space-y-6">
      <div className="select-none">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          在此查看选定会话的元信息与完整已持久化对话。您也可以随时返回至聊天控制面板继续对话。
        </p>
      </div>

      {!conversationId ? (
        <ErrorState message="缺少会话 ID，无法加载详情。" />
      ) : null}

      {conversationId && conversationQuery.isLoading ? (
        <Card className="flex items-center justify-center p-8">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-500"></span>
            </span>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">正在加载会话详情...</p>
          </div>
        </Card>
      ) : null}

      {conversationId && conversationQuery.isError ? (
        <ErrorState message={conversationQuery.error.message} />
      ) : null}

      {conversationId &&
      !conversationQuery.isLoading &&
      !conversationQuery.isError &&
      conversationQuery.data ? (
        <>
          <Card className="space-y-5 border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between border-b border-slate-100 dark:border-slate-800/50 pb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 font-display">
                  {conversationQuery.data.title || "未命名会话"}
                </h2>
                <p className="mt-1 break-all text-xs font-mono text-slate-400 dark:text-slate-500">
                  会话 ID: {conversationQuery.data.id}
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  navigate(
                    buildContinueUrl(conversationQuery.data!.id),
                  );
                }}
                className="text-xs font-semibold px-4 py-1.5 self-start lg:self-auto shrink-0"
              >
                继续对话
              </Button>
            </div>

            <div className="grid gap-4 text-xs md:grid-cols-4 pt-1">
              <div>
                <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                  发起用户
                </p>
                <p className="mt-1 break-all text-slate-700 dark:text-slate-300">
                  {conversationQuery.data.userId ?? GUEST_USER_LABEL}
                </p>
              </div>
              <div>
                <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                  绑定 Agent
                </p>
                <p className="mt-1 text-slate-700 dark:text-slate-300 font-mono">
                  {conversationQuery.data.agentId ?? "chat_agent"}
                </p>
              </div>
              <div>
                <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                  创建时间
                </p>
                <p className="mt-1 text-slate-700 dark:text-slate-300">
                  {conversationQuery.data.createdAt
                    ? formatDate(conversationQuery.data.createdAt)
                    : "暂无"}
                </p>
              </div>
              <div>
                <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                  已归档消息数
                </p>
                <p className="mt-1 text-slate-700 dark:text-slate-300 font-bold">{messages.length}</p>
              </div>
            </div>
          </Card>

          {messages.length === 0 ? (
            <EmptyState
              title="暂无持久化消息"
              description="本会话目前不包含任何已归档的流式或同步历史消息记录。"
            />
          ) : (
            <Card className="space-y-4 border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6">
              <div className="border-b border-slate-100 dark:border-slate-800/50 pb-3 select-none">
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">历史消息流</h2>
                <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                  以下为后端已归档的真实历史消息列表，不可修改。
                </p>
              </div>
              
              <div className="rounded-[24px] border border-slate-200/60 bg-slate-50/40 p-4 dark:border-slate-800/80 dark:bg-slate-950/40">
                <ScrollArea className="max-h-[520px] pr-2">
                  <MessageList messages={messages} />
                </ScrollArea>
              </div>
            </Card>
          )}
        </>
      ) : null}
    </section>
  );
}
