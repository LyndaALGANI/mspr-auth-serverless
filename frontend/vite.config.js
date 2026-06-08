import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 8080,
    proxy: {
      '/function': {
        target: 'http://51.210.104.236',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
