import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 5173, proxy: { "/api": process.env.DEV_PROXY_TARGET ?? "http://localhost:8000" } },
});
