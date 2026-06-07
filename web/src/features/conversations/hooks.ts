import { useQuery } from "@tanstack/react-query";

import {
  getConversationDetail,
  getConversations,
} from "@/features/conversations/api";
import { QUERY_KEYS } from "@/shared/constants/query-keys";

export function useConversations() {
  return useQuery({
    queryKey: QUERY_KEYS.conversations,
    queryFn: getConversations,
  });
}

export function useConversationDetail(conversationId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.conversationDetail(conversationId),
    queryFn: () => getConversationDetail(conversationId),
    enabled: Boolean(conversationId),
  });
}
