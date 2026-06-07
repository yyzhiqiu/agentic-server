import { useMutation } from "@tanstack/react-query";

import { sendAgentChat } from "@/features/chat/api";

export function useChat() {
  return useMutation({
    mutationFn: sendAgentChat,
  });
}
