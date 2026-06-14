import { MessageBubble } from "@/pages/chat/components/MessageBubble";
import type { ExecutionActivity } from "@/pages/chat/chatTimeline";

type Message = {
  id: string;
  role: string;
  content: string;
  pending?: boolean;
  activities?: ExecutionActivity[];
};

type MessageListProps = {
  messages: Message[];
};

export function MessageList({ messages }: MessageListProps) {
  return (
    <div className="space-y-3">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          content={message.content}
          role={message.role}
          pending={message.pending}
          activities={message.activities}
        />
      ))}
    </div>
  );
}
