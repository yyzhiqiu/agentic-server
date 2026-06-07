import { useMutation } from "@tanstack/react-query";

import { sendChat } from "@/features/chat/api";

export function useChat() {
  return useMutation({
    mutationFn: sendChat,
  });
}
