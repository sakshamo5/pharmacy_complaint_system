import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy all /api calls to FastAPI backend during dev
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Disable proxy buffering so SSE events flow through immediately
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.removeHeader('accept-encoding');
          });
        },
      },
    },
  },
})
