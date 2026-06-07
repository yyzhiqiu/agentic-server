import { MessageBubble } from "@/pages/chat/components/MessageBubble";

type Message = {
  id: string;
  role: string;
  content: string;
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
        />
      ))}
    </div>
  );
}
