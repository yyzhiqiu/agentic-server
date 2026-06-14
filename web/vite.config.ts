import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3100,
    host: "127.0.0.1",
    proxy: {
      "/v1": {
        target: "http://127.0.0.1:8100",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:8100",
        changeOrigin: true,
      },
      "/ready": {
        target: "http://127.0.0.1:8100",
        changeOrigin: true,
      },
    },
  },
});
