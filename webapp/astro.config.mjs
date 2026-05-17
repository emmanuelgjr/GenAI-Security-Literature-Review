import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://emmanuelgjr.github.io',
  base: '/GenAI-Security-Literature-Review/',
  trailingSlash: 'always',
  integrations: [preact(), sitemap()],
  output: 'static',
});
