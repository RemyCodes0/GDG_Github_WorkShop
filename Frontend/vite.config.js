import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rolldownOptions: {
      input: {
        app: fileURLToPath(new URL('./index.html', import.meta.url)),
        projectCard: fileURLToPath(new URL('./project-card.html', import.meta.url)),
      },
    },
  },
})
