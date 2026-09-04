// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';

// ⚠️ 部署前改成你的真实域名
const SITE = 'https://blog.example.com';

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
