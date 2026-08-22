import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // MapLibre GL JS is large by design — suppress the warning
    chunkSizeWarningLimit: 1500,
  },
})
