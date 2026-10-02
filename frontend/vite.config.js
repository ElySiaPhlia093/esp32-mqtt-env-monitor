import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发时后端在 8000 端口，前端 5173 端口，通过代理解决跨域
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
