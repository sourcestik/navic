import { defineConfig } from 'vite';

const apiPaths = ['/health', '/coverage', '/route', '/geocode', '/reverse-geocode', '/network', '/docs', '/openapi.json'];
export default defineConfig({
  server: { proxy: Object.fromEntries(apiPaths.map(path => [path, 'http://127.0.0.1:8080'])) },
  build: { target: 'es2022' },
});
