
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // GitHub repository: manya302/Watt_and_Where
  base: "/Watt_and_Where/",
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
