import { RefreshCcw } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useConversations } from "@/features/conversations/hooks";
import { EmptyState } from "@/shared/components/feedback/EmptyState";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { LoadingState } from "@/shared/components/feedback/LoadingState";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { GUEST_USER_LABEL } from "@/shared/constants/app";
import { ROUTES } from "@/shared/constants/routes";
import { formatDate } from "@/shared/lib/date";

export function ConversationListPage() {
  const navigate = useNavigate();
  const conversationsQuery = useConversations();
  const conversations = conversationsQuery.data?.items ?? [];
  const total = conversationsQuery.data?.total ?? 0;

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-brand-700">
            Conversations
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">会话列表</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            这里展示已持久化的历史会话，并保留搜索、分页和筛选等扩展空间。
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            void conversationsQuery.refetch();
          }}
          disabled={conversationsQuery.isFetching}
          className="gap-2"
        >
          <RefreshCcw
            size={16}
            className={conversationsQuery.isFetching ? "animate-spin" : ""}
          />
          刷新列表
        </Button>
      </div>

      <Card>
        <p className="text-sm text-slate-500">会话总数</p>
        <p className="mt-3 text-3xl font-semibold text-slate-900">{total}</p>
      </Card>

      {conversationsQuery.isLoading ? (
        <LoadingState title="正在加载会话列表..." />
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
          title="还没有历史会话"
          description="会话列表接口已经接通。创建新对话后，这里会展示可直接查看的历史会话。"
        />
      ) : null}

      {!conversationsQuery.isLoading && !conversationsQuery.isError && total > 0 ? (
        <div className="grid gap-4">
          {conversations.map((conversation) => (
            <Card key={conversation.id} className="space-y-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <h2 className="truncate text-lg font-semibold text-slate-900">
                    {conversation.title ?? "未命名会话"}
                  </h2>
                  <p className="mt-1 break-all text-sm text-slate-500">
                    会话 ID: {conversation.id}
                  </p>
                </div>
                <Badge>历史会话</Badge>
              </div>

              <div className="grid gap-3 text-sm text-slate-600 md:grid-cols-2">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    创建时间
                  </p>
                  <p className="mt-1 text-slate-700">
                    {conversation.createdAt
                      ? formatDate(conversation.createdAt)
                      : "暂无"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    用户
                  </p>
                  <p className="mt-1 break-all text-slate-700">
                    {conversation.userId ?? GUEST_USER_LABEL}
                  </p>
                </div>
              </div>

              <div className="flex justify-end">
                <Button
                  size="sm"
                  onClick={() => {
                    navigate(`${ROUTES.conversations}/${conversation.id}`);
                  }}
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
