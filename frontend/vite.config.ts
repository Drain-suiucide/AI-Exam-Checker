import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendPort = env.VITE_BACKEND_PORT ?? "8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      // Единый origin в разработке: /api проксируется на backend,
      // поэтому CORS не нужен (ADR-001).
      proxy: {
        "/api": {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["src/test/setup.ts"],
    },
  };
});
