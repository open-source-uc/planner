import { defineConfig, loadEnv } from 'vite'
import { sentryVitePlugin } from "@sentry/vite-plugin"
import react from '@vitejs/plugin-react'
import eslintPlugin from '@nabla/vite-plugin-eslint'
import svgr from 'vite-plugin-svgr'

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.BACKEND_API_URL
  if (typeof backendUrl !== 'string') {
    throw new Error('BACKEND_API_URL environment variable not set during build')
  }
  return {
    build: {
      sourcemap: true,
    },
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
      watch: {
        usePolling: true
      }
    },
    plugins: [
      react(), 
      eslintPlugin(), 
      svgr(), 
      sentryVitePlugin({
        authToken: process.env.SENTRY_AUTH_TOKEN,
        org: "planner-ing-uc",
        project: "planner-frontend",
      })
    ],
  }
})
