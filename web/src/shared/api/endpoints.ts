export const API_ENDPOINTS = {
  chat: "/v1/chat",
  chatStream: "/v1/chat/stream",
  conversations: "/v1/conversations",
  agentRuns: "/v1/agent/runs",
  files: "/v1/files",
  fileUpload: "/v1/files/upload",
  fileDetail: (fileId: string) => `/v1/files/${fileId}`,
  fileDownload: (fileId: string) => `/v1/files/${fileId}/download`,
} as const;
