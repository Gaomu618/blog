// 站点配置
export const SITE_TITLE = 'Tagaki';
export const SITE_DESCRIPTION = '一位 Java 的小小学习者，记录学习过程。';
export const SITE_AUTHOR = 'Tagaki';

// Cloudflare Pages 部署地址
export const SITE_URL = 'https://blog-6d5.pages.dev';

export const NAV_LINKS = [
  { href: '/', label: '文章' },
  { href: '/posts/', label: '归档' },
  { href: '/tags/', label: '标签' },
  { href: '/about/', label: '关于' },
];

// 评论系统暂未启用(giscus 在国内被 GFW 拦截,Twikoo Vercel 部署访问不稳)
// 留空,以后想用再启用
