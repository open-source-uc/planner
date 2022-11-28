import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import eslintPlugin from '@nabla/vite-plugin-eslint';
import svgrPlugin from 'vite-plugin-svgr';



// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), eslintPlugin(), svgrPlugin()]
})
