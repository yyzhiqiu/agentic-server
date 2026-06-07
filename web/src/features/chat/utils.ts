import type { ChatMessage } from "@/features/chat/types";

export function getLastMessage(messages: ChatMessage[]) {
  return messages[messages.length - 1] ?? null;
}
