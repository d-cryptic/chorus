import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  // emptyOutDir stays FALSE on purpose: outDir is ../public, which also holds hand-written
  // review.html, index-convex.html and fonts/ — emptying it would delete them. Vite owns only
  // assets/, so `prebuild` clears exactly that. Without it, old hashed bundles accumulate and
  // get committed: 7 of them kept the read-provider's name alive in a PUBLIC repo for weeks
  // after the source stopped naming it.
  build: { outDir: "../public", emptyOutDir: false },
});
