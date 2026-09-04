---
title: 我的第一篇博客：从零搭建 Astro 个人博客
description: 终于决定开博客了。记录一下从技术选型到上线的整个过程。
pubDate: 2026-09-05
tags: [Astro, Blog]
---

## 为什么要开博客

想了很久要不要开博客。技术社区里博客写了很多年，但自己的"主阵地"一直没有——笔记散落在 Notion、博客发在掘金、思考留在 Twitter。直到最近才意识到：**如果没有一个属于自己的、长期积累的地方，所有内容都只是过客**。

所以这次决定认真做：选好技术栈、做好设计、长期写下去。

## 技术栈选择

我的需求很明确——写作体验好、托管免费、维护成本低、加载快。考察了一圈后，结论是：**Astro + Vercel + Markdown**。

几个备选方案的对比：

- **Astro**：内容驱动、零 JS 默认、可以用任意框架组件，2026 年最推荐
- **Hugo**：极快但模板语言老，学习曲线陡
- **Hexo**：中文社区大但性能落后
- **WordPress**：需要买服务器、自己维护

### 安装

一行命令就够：

```bash
npm create astro@latest my-blog -- --template blog --typescript strict
```

脚手架会问几个问题——装 npm 包、要不要 git、要不要 TypeScript。选完后就能 `npm run dev` 看到默认博客了。

### 配置文件

Astro 的核心配置在 `astro.config.mjs`：

```js
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';

export default defineConfig({
  site: 'https://blog.example.com',
  integrations: [sitemap(), mdx()],
  markdown: {
    shikiConfig: {
      theme: 'github-dark',
      wrap: true,
    },
  },
});
```

> 一个细节：Astro 内置的 Shiki 代码高亮是构建时执行的，访问者浏览器不需要加载 Prism/Highlight.js 这类运行时库。这意味着代码块的渲染零运行时成本——这是 Astro 比 Next.js 性能好的关键之一。

## 内容管理

文章用 Markdown 写，放在 `src/content/blog/` 目录下。Astro 的 Content Collections 让我能定义 schema，写作时编辑器会给出类型提示和验证。

```ts
// src/content.config.ts
import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    tags: z.array(z.string()).default([]),
  }),
});

export const collections = { blog };
```

## 部署到 Vercel

本地写好文章、git push，剩下交给 Vercel。它会自动识别 Astro 项目、跑构建、部署到全球 CDN。首次部署大约 1-2 分钟，后续推送 30 秒内上线。

整个过程不需要碰服务器、不需要配 nginx、不需要管证书。这就是现代静态站点的优雅之处——*你只管写，平台负责其余一切*。

---

这就是开博客的第一步。下一篇会写 Content Collections 的进阶用法、怎么加评论、怎么配置自定义域名。持续更新，欢迎订阅 RSS。
