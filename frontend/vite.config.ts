import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000' },
  },
  build: {
    rollupOptions: {
      // Recharts (+ d3) is most of the bundle; keep it and React in their own cacheable chunks.
      output: {
        manualChunks: { react: ['react', 'react-dom', 'react-router-dom'], charts: ['recharts'] },
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
});
