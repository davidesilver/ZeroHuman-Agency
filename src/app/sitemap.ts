import type { MetadataRoute } from 'next'

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://zerohuman.vercel.app'

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date().toISOString()

  // Static marketing pages — expand as (marketing) route group grows
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: BASE_URL,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 1.0,
    },
    // Uncomment as pages are built:
    // { url: `${BASE_URL}/features`, lastModified: now, changeFrequency: 'monthly', priority: 0.8 },
    // { url: `${BASE_URL}/use-cases/agencies`, lastModified: now, changeFrequency: 'monthly', priority: 0.7 },
    // { url: `${BASE_URL}/use-cases/teams`, lastModified: now, changeFrequency: 'monthly', priority: 0.7 },
    // { url: `${BASE_URL}/use-cases/creators`, lastModified: now, changeFrequency: 'monthly', priority: 0.7 },
    // { url: `${BASE_URL}/compare/jasper`, lastModified: now, changeFrequency: 'monthly', priority: 0.6 },
    // { url: `${BASE_URL}/compare/copy-ai`, lastModified: now, changeFrequency: 'monthly', priority: 0.6 },
    // { url: `${BASE_URL}/blog`, lastModified: now, changeFrequency: 'daily', priority: 0.8 },
  ]

  // TODO: dynamically add blog posts from MDX content directory
  // const blogPosts = getBlogSlugs().map(slug => ({
  //   url: `${BASE_URL}/blog/${slug}`,
  //   lastModified: getPostDate(slug),
  //   changeFrequency: 'monthly' as const,
  //   priority: 0.6,
  // }))

  return [...staticPages]
}
