import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    // Bound concurrent DOM environments on the personal development host.
    maxWorkers: 2,
    setupFiles: './src/test/setup.ts',
  },
})
