import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const htmlBypass = (req) => {
  if (req.headers.accept && req.headers.accept.includes("text/html")) {
    return "/index.html";
  }
};

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "^/health": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
      "^/auth": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
      "^/organization": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
      "^/dashboard/": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
      "^/findings": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
      "^/recommendations": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
      "^/budgets": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
      "^/reports": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
      "^/forecast": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
      "^/sync": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
});
