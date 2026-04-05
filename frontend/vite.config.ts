import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    hmr: {
      host: "localhost",
      protocol: "ws",
      port: 5173,
      clientPort: 5173,
    },
  },
  preview: {
    host: "0.0.0.0",
    allowedHosts: ["reservas-deportivas.up.railway.app", "app.reservas-deportivas.com"],
  },
});
