import { RefreshCcw } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useConversations } from "@/features/conversations/hooks";
import { EmptyState } from "@/shared/components/feedback/EmptyState";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { GUEST_USER_LABEL } from "@/shared/constants/app";
import { ROUTES } from "@/shared/constants/routes";
import { formatDate } from "@/shared/lib/date";

function buildContinueUrl(conversationId: string) {
  const params = new URLSearchParams();
  params.set("conversationId", conversationId);
  return `${ROUTES.chat}?${params.toString()}`;
}

export function ConversationListPage() {
  const navigate = useNavigate();
  const conversationsQuery = useConversations();
  const conversations = conversationsQuery.data?.items ?? [];
  const total = conversationsQuery.data?.total ?? 0;

  return (
    <section className="h-full overflow-y-auto pr-2 space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between select-none">
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            在此查看与管理您所有的历史对话记录。您可以随时选择继续对话或深入查看执行链。
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            void conversationsQuery.refetch();
          }}
          disabled={conversationsQuery.isFetching}
          className="gap-2 self-start lg:self-auto text-xs"
        >
          <RefreshCcw
            size={14}
            className={conversationsQuery.isFetching ? "animate-spin" : ""}
          />
          <span>刷新列表</span>
        </Button>
      </div>

      <Card className="max-w-xs border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-5">
        <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">历史会话总数</p>
        <p className="mt-2 text-3xl font-extrabold text-slate-900 dark:text-slate-100 font-display">{total}</p>
      </Card>

      {conversationsQuery.isLoading ? (
        <Card className="flex items-center justify-center p-8">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-500"></span>
            </span>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">正在加载会话列表...</p>
          </div>
        </Card>
      ) : null}

      {conversationsQuery.isError ? (
        <div className="space-y-3">
          <ErrorState message={conversationsQuery.error.message} />
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              void conversationsQuery.refetch();
            }}
          >
            重新加载
          </Button>
        </div>
      ) : null}

      {!conversationsQuery.isLoading && !conversationsQuery.isError && total === 0 ? (
        <EmptyState
          title="暂无会话历史"
          description="当前尚未检测到任何已归档的会话。请前往对话控制台发起第一次多智能体协作交流。"
        />
      ) : null}

      {!conversationsQuery.isLoading && !conversationsQuery.isError && total > 0 ? (
        <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
          {conversations.map((conversation) => (
            <Card
              key={conversation.id}
              className="space-y-4 border border-slate-200 bg-white/70 dark:border-slate-800/80 dark:bg-slate-900/60 shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5"
            >
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between border-b border-slate-100 dark:border-slate-800/50 pb-3">
                <div className="min-w-0">
                  <h2 className="truncate text-base font-bold text-slate-900 dark:text-slate-100 font-display">
                    {conversation.title || "未命名会话"}
                  </h2>
                  <p className="mt-1 break-all text-xs font-mono text-slate-400 dark:text-slate-500">
                    ID: {conversation.id}
                  </p>
                </div>
                <Badge variant="default" className="self-start lg:self-auto shrink-0 font-mono text-[10px]">
                  {conversation.agentId || "coordinator_agent"}
                </Badge>
              </div>

              <div className="grid gap-4 text-xs md:grid-cols-3">
                <div>
                  <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                    创建时间
                  </p>
                  <p className="mt-1 text-slate-700 dark:text-slate-350">
                    {conversation.createdAt
                      ? formatDate(conversation.createdAt)
                      : "暂无记录"}
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                    用户账户
                  </p>
                  <p className="mt-1 break-all text-slate-700 dark:text-slate-350">
                    {conversation.userId ?? GUEST_USER_LABEL}
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                    路由 Agent
                  </p>
                  <p className="mt-1 break-all text-slate-700 dark:text-slate-350 font-mono">
                    {conversation.agentId ?? "chat_agent"}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap justify-end gap-2 pt-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    navigate(buildContinueUrl(conversation.id));
                  }}
                  className="text-xs font-semibold px-4 py-1.5"
                >
                  继续对话
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    navigate(`${ROUTES.conversations}/${conversation.id}`);
                  }}
                  className="text-xs font-semibold px-4 py-1.5"
                >
                  查看详情
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : null}
    </section>
  );
}
