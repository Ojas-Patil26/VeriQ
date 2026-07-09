import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, API calls are proxied to the local FastAPI backend so no CORS setup
// is needed. In production the app calls VITE_API_URL directly.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080',
      '/health': 'http://localhost:8080',
    },
  },
})
