import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: /api is proxied to the backend. Prod: VITE_API_BASE_URL is baked in at build time.
export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 5173, proxy: { "/api": process.env.DEV_PROXY_TARGET ?? "http://localhost:8000" } },
});
