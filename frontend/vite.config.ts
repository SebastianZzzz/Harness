import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
<<<<<<< HEAD
        target: 'http://127.0.0.1:8001',
=======
        target: 'http://127.0.0.1:8000',
>>>>>>> feat/frontend2
        changeOrigin: true,
        secure: false,
      },
      '/health': {
<<<<<<< HEAD
        target: 'http://127.0.0.1:8001',
=======
        target: 'http://127.0.0.1:8000',
>>>>>>> feat/frontend2
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
<<<<<<< HEAD
        target: 'ws://127.0.0.1:8001',
=======
        target: 'ws://127.0.0.1:8000',
>>>>>>> feat/frontend2
        ws: true,
        secure: false,
      },
    },
  },
});
