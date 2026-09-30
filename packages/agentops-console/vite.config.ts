import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiPort = process.env.AGENTOPS_API_PORT ?? "8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: `http://localhost:${apiPort}`, changeOrigin: true, rewrite: (p: string) => p.replace(/^\/api/, "") } },
  },
  test: { environment: "jsdom", globals: true, setupFiles: [] },
});
