import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import { loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import basicSsl from '@vitejs/plugin-basic-ssl'


const repositoryRoot = fileURLToPath(new URL('..', import.meta.url))

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, repositoryRoot, '')

  return {
    publicDir: 'assets',
    plugins: [vue(), basicSsl()],
    server: {
      proxy: {
        '/api': {
          target: process.env.VITE_API_TARGET || env.VITE_API_TARGET || 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
