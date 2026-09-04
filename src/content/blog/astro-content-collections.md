---
title: Astro 内容集合进阶：让 Markdown 成为一等公民
description: Content Collections 是 Astro 最让我惊艳的特性——用 TypeScript schema 验证 frontmatter，再也不用担心字段拼错。
pubDate: 2026-09-01
tags: [Astro]
---

## 什么是 Content Collections

Astro 5 的 Content Collections 是一套"类型安全的内容管理"机制：你用 `defineCollection` 声明结构（Markdown 在哪里、有哪些 frontmatter 字段、字段类型是什么），Astro 在构建时校验每篇文章，自动生成 TypeScript 类型，写代码时编辑器能给完整的类型提示。

听起来抽象，用一个例子说明：

## 基础用法

```ts
// src/content.config.ts
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

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

这段代码告诉 Astro：

1. **哪里找文章**：`./src/content/blog` 目录下所有 `.md` 文件
2. **结构校验**：每篇文章必须包含 `title`、`description`、`pubDate` 字段
3. **类型转换**：`pubDate` 字符串会被解析成 `Date` 对象
4. **默认值**：`tags` 不写默认空数组

## 写文章时的体验

在 `src/content/blog/` 下新建 `my-post.md`：

```markdown
---
title: 文章标题
description: 简介
pubDate: 2026-09-01
tags: [Tech, Note]
---

正文用 Markdown 写。
```

写错字段名 Astro 会在构建时报错——比如 `pubdate` 写成 `publishDate`：

```
Error: Frontmatter "publishDate" invalid:
  - "publishDate" is not allowed
```

## 在页面里用

```astro
---
import { getCollection } from 'astro:content';

const posts = (await getCollection('blog'))
  .sort((a, b) => b.data.pubDate.getTime() - a.data.pubDate.getTime());
---

<ul>
  {posts.map((post) => (
    <li>
      <a href={`/posts/${post.id}/`}>{post.data.title}</a>
      <time>{post.data.pubDate.toLocaleDateString()}</time>
    </li>
  ))}
</ul>
```

`post.data.title` 在这里有完整的类型提示，IDE 会列出所有可用字段。

## 进阶：自定义校验

zod 的能力远不止基础类型。比如强制要求每篇文章至少一个标签：

```ts
tags: z.array(z.string()).min(1, '至少一个标签'),
```

或者用枚举限制可选值：

```ts
status: z.enum(['draft', 'published']).default('draft'),
```

## 为什么这个设计好

对比一下没用 Collections 的情况：

| 方式 | 字段错了会怎样 |
|---|---|
| 不用 Collections | 运行时才发现，404 之类的诡异错误 |
| 用 Collections | 构建时直接报错，告诉你哪个文件哪一行错了 |

构建时校验 = 部署前拦截所有内容错误。这对长期维护的博客尤其重要——你不会想在写了一年后突然发现三年前的某篇文章 frontmatter 拼错了导致页面崩了。

## 小结

Content Collections 看似只是个 schema 校验，但它把"内容"提升到了"代码同等地位"——类型安全、自动补全、构建时校验。这是我用 Astro 写博客最重要的原因之一。
