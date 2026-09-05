// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';

// Cloudflare Pages 部署地址
const SITE = 'https://blog-6d5.pages.dev';

export default defineConfig({
  site: SITE,
  integrations: [sitemap(), mdx()],
  markdown: {
    shikiConfig: {
      themes: {
        light: 'github-light',
        dark: 'github-dark',
      },
      wrap: true,
    },
  },
});
