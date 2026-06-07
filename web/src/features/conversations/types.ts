export type ConversationMetadata = Record<string, unknown>;

export type ConversationMessage = {
  id: string;
  conversationId: string;
  role: string;
  content: string;
  metadata: ConversationMetadata;
  createdAt: string | null;
};

export type ConversationListItem = {
  id: string;
  title: string | null;
  userId: string | null;
  metadata: ConversationMetadata;
  createdAt: string | null;
};

export type ConversationListResponse = {
  items: ConversationListItem[];
  total: number;
};

export type ConversationDetail = ConversationListItem & {
  messages: ConversationMessage[];
};
