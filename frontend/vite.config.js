import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  // Staging serves the built app under a sub-path (VITE_BASE_PATH, e.g.
  // /apps/staging/). Defaults to / for local development.
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  server: {
    // Proxy API calls to the FastAPI backend during development.
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },
    },
  },
})
