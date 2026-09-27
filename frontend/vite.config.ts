import { readFileSync } from 'node:fs'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const useLocalHttps = process.env.VITE_DEV_HTTPS === 'true'

export default defineConfig({
  plugins: [react()],
  server: {
    https: useLocalHttps
      ? {
          cert: readFileSync('/certs/academia-local.pem'),
          key: readFileSync('/certs/academia-local-key.pem'),
        }
      : undefined,
    proxy: useLocalHttps
      ? {
          '/api': {
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/api/, ''),
            target: 'http://backend:8000',
          },
        }
      : undefined,
  },
})
