import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,           // 开启 WebSocket 代理
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
