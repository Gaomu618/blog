// 站点配置
export const SITE_TITLE = 'Tagaki';
export const SITE_DESCRIPTION = '一位 Java 的小小学习者，记录学习过程。';
export const SITE_AUTHOR = 'Tagaki';

// ⚠️ 部署前改成你的真实域名（暂留占位，部署时再改）
export const SITE_URL = 'https://blog.example.com';

export const NAV_LINKS = [
  { href: '/', label: '文章' },
  { href: '/posts/', label: '归档' },
  { href: '/tags/', label: '标签' },
  { href: '/about/', label: '关于' },
];

// giscus 评论配置
// ⚠️ repo 已填好，但 repoId/categoryId 必须你自己去 https://giscus.app 生成
// 步骤：1) 在 GitHub 仓库开启 Discussions → 2) 填仓库名自动生成 ID → 3) 把下面两个 placeholder 替换
// 如果不想用评论，访问时会自动隐藏，不影响博客
export const GISCUS = {
  repo: 'Gaomu618/blog',
  repoId: 'R_placeholder_replace_me',
  category: 'General',
  categoryId: 'DIC_placeholder_replace_me',
  mapping: 'pathname' as const,
  strict: '0' as const,
  reactionsEnabled: '1' as const,
  emitMetadata: '0' as const,
  inputPosition: 'bottom' as const,
  theme: 'preferred_color_scheme' as const,
  lang: 'zh-CN' as const,
};
