import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// The backend runs on 127.0.0.1:8000. Proxying /api keeps the browser on one origin (no
// CORS setup needed) and avoids Windows' slow IPv6-first "localhost" lookup.
const BACKEND_URL = process.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: BACKEND_URL, changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
