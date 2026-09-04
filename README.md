# my-blog

Astro 个人博客 — 静态生成 + 免费托管 + 暗/亮双主题 + 6 套调色板 + giscus 评论。

## 技术栈

- **Astro 5** — 内容驱动的静态站点生成器
- **MDX** — 在 Markdown 里写 React/Vue 组件
- **Shiki** — 构建时语法高亮（零运行时）
- **TypeScript** — 严格模式
- **giscus** — 基于 GitHub Discussions 的评论系统
- **Vercel** — 部署和全球 CDN

## 快速开始

```bash
# 安装依赖
npm install

# 本地开发（默认 http://localhost:4321）
npm run dev

# 构建生产版本
npm run build

# 预览构建产物
npm run preview
```

## 目录结构

```
src/
├── components/         可复用组件
│   ├── Header.astro
│   ├── Footer.astro
│   ├── ThemeSwitcher.astro
│   ├── PostCard.astro
│   ├── TOC.astro
│   └── Giscus.astro
├── content/
│   └── blog/           所有文章（Markdown）
├── content.config.ts   Content Collections schema
├── layouts/
│   ├── BaseLayout.astro
│   └── PostLayout.astro
├── pages/
│   ├── index.astro     主页
│   ├── about.astro
│   ├── rss.xml.js
│   ├── posts/
│   │   ├── index.astro        归档
│   │   └── [...slug].astro    文章详情
│   └── tags/
│       ├── index.astro        标签云
│       └── [tag].astro        单标签页
├── styles/
│   └── global.css     设计系统 + 所有样式
└── consts.ts          站点配置（部署前必改）
```

## 写新文章

在 `src/content/blog/` 下新建 `.md` 文件：

```markdown
---
title: 文章标题
description: 简介（会显示在卡片和搜索结果中）
pubDate: 2026-09-05
tags: [标签1, 标签2]
---

正文用 Markdown 写。支持：
- 标题（自动生成目录）
- 代码块（自动语法高亮）
- 引用、列表、表格
- 数学公式（需额外配置）

部署后会自动出现在主页、归档页、对应标签页。
```

## 部署到 Vercel

部署前要改 2 处：

### 1. 改 `astro.config.mjs`

```js
const SITE = 'https://你的域名.com';  // ← 改成你的实际域名
```

### 2. 改 `src/consts.ts`

```ts
export const SITE_URL = 'https://你的域名.com';  // ← 改成你的实际域名

// giscus 评论（可选）
// 注册步骤：https://giscus.app/zh-CN
//   1. 在 GitHub 仓库开启 Discussions
//   2. 在 https://giscus.app 填入仓库名，自动生成下面的值
export const GISCUS = {
  repo: '你的用户名/你的仓库名',
  repoId: 'R_xxx',
  category: 'General',
  categoryId: 'DIC_xxx',
  // ... 其他保持默认
};
```

### 3. 推送 GitHub

```bash
# 在 GitHub 上新建一个空仓库 my-blog
git init
git add .
git commit -m "init"
git branch -M main
git remote add origin https://github.com/你的用户名/my-blog.git
git push -u origin main
```

### 4. Vercel 部署

1. 打开 https://vercel.com，用 GitHub 登录
2. 点 **Add New → Project**
3. 选 `my-blog` 仓库 → **Import**
4. Framework Preset 自动识别为 Astro
5. 点 **Deploy**
6. 1-2 分钟后得到 `https://my-blog-xxx.vercel.app`

之后每次 `git push` 都会自动部署。

## 主题与调色板

博客支持 12 种颜色组合 = 2 种模式（亮/暗）× 6 套调色板（蓝/绿/橙/紫/粉/单色）。读者在右上角切换，所有偏好保存在 localStorage。

想加新调色板？在 `src/styles/global.css` 里加一行：

```css
[data-palette="teal"] { --primary: #14b8a6; --primary-fg: #fff; --accent-soft: #ccfbf1; --accent-fg: #134e4a; }
[data-mode="dark"][data-palette="teal"] { --accent-soft: rgba(20, 184, 166, 0.15); --accent-fg: #5eead4; }
```

然后在 `src/components/ThemeSwitcher.astro` 加按钮。

## 性能

- 默认零 JS（除主题切换器的 < 2KB 内联脚本）
- 字体 swap 加载，woff2 子集
- 代码块 Shiki 构建时着色，运行时零成本
- 静态 HTML，可被任意 CDN 缓存

## 后续可加

- 全站搜索（[Pagefind](https://pagefind.app/)，几行集成）
- 数学公式（`remark-math` + `rehype-katex`）
- 图片优化（`astro:assets` 的 `<Image>` 组件）
- 访问统计（Plausible / Umami 免费版）
- 自定义域名（Vercel 控制台添加，几条 DNS 记录）

## License

MIT
