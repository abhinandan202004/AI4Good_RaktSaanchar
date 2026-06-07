import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // usePolling only needed inside Docker on Windows dev — disabled for prod builds
    watch: {
      usePolling: process.env.NODE_ENV !== 'production',
    },
  },
})
