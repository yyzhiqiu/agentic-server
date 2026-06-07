import { Navigate, createBrowserRouter } from "react-router-dom";

import { AgentRunDetailPage } from "@/pages/agent-runs/AgentRunDetailPage";
import { AgentRunsPage } from "@/pages/agent-runs/AgentRunsPage";
import { ChatPage } from "@/pages/chat/ChatPage";
import { ConversationDetailPage } from "@/pages/conversations/ConversationDetailPage";
import { ConversationListPage } from "@/pages/conversations/ConversationListPage";
import { FilesPage } from "@/pages/files/FilesPage";
import { NotFoundPage } from "@/pages/not-found/NotFoundPage";
import { SettingsPage } from "@/pages/settings/SettingsPage";
import { AppLayout } from "@/shared/components/layout/AppLayout";
import { ROUTES } from "@/shared/constants/routes";

export const router = createBrowserRouter([
  {
    path: ROUTES.home,
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Navigate to={ROUTES.chat} replace />,
      },
      {
        path: ROUTES.chat,
        element: <ChatPage />,
      },
      {
        path: ROUTES.conversations,
        element: <ConversationListPage />,
      },
      {
        path: `${ROUTES.conversations}/:conversationId`,
        element: <ConversationDetailPage />,
      },
      {
        path: ROUTES.agentRuns,
        element: <AgentRunsPage />,
      },
      {
        path: `${ROUTES.agentRuns}/:runId`,
        element: <AgentRunDetailPage />,
      },
      {
        path: ROUTES.files,
        element: <FilesPage />,
      },
      {
        path: ROUTES.settings,
        element: <SettingsPage />,
      },
      {
        path: "*",
        element: <NotFoundPage />,
      },
    ],
  },
]);
