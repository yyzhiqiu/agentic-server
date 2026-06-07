import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "@/App";
import { AppProviders } from "@/app/providers";
import { APP_NAME } from "@/shared/constants/app";
import "@/styles/globals.css";

document.title = APP_NAME;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProviders>
      <App />
    </AppProviders>
  </React.StrictMode>,
);
