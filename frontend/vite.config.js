import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // the React dev server calls /api/... and Vite forwards it to FastAPI,
    // so the browser sees one origin and CORS never comes into it
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
