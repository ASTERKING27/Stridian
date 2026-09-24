import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  define: {
    // true only in builds Vercel makes, so a copy built and served on a laptop never
    // asks for Vercel's analytics script (it isn't there, and would 404)
    __ON_VERCEL__: JSON.stringify(Boolean(process.env.VERCEL)),
  },
  server: {
    // the React dev server calls /api/... and Vite forwards it to FastAPI,
    // so the browser sees one origin and CORS never comes into it
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
