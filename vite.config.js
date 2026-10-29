import {defineConfig} from 'vite';
export default defineConfig({server:{proxy:{'/api':'http://127.0.0.1:8000'}},build:{outDir:'dist',rollupOptions:{output:{manualChunks(id){if(id.includes('demo.json'))return 'sample-trip';if(id.includes('leaflet'))return 'map';if(id.includes('node_modules'))return 'vendor'}}}}});
