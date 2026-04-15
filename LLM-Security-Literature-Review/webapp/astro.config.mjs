import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  site: 'https://emmanuelgjr.github.io',
  base: '/GenAI-Security-Literature-Review',
  integrations: [preact(), tailwind()],
  output: 'static',
});
