import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
const apiTarget = process.env.VITE_API_TARGET || 'http://localhost:8011'

export default defineConfig({
  // Staging serves the built app under a sub-path (VITE_BASE_PATH, e.g.
  // /apps/staging/). Defaults to / for local development.
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] }),
    tailwindcss(),
  ],
  server: {
    // Proxy API calls to the FastAPI backend during development.
    // If the backend is running through Docker Compose, set:
    //   VITE_API_TARGET=http://localhost:8011
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
