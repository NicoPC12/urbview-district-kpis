/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

/**
 * Vite configuration.
 *
 * - `/api` is proxied to the backend so the browser stays same-origin and Django needs no
 *   CORS configuration. The target defaults to the compose service name.
 * - `usePolling` is opt-in via `VITE_USE_POLLING`: Docker Desktop on Windows does not forward
 *   inotify events through bind mounts, so compose turns it on; a native run leaves it off.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const usePolling = env.VITE_USE_POLLING === 'true';

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      host: true,
      port: 5173,
      strictPort: true,
      watch: usePolling ? { usePolling: true, interval: 500 } : undefined,
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: false,
      setupFiles: ['./tests/setup.ts'],
      include: ['tests/**/*.test.{ts,tsx}', 'src/**/*.test.{ts,tsx}'],
      css: false,
    },
  };
});
