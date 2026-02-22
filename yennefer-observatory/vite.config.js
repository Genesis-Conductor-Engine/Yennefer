import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/Yennefer/', // Set base path for GitHub Pages deployment
  server: {
    port: 5173,
    host: true
  }
})
