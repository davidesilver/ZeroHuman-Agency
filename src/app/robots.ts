import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: [
          '/',
          '/features',
          '/blog',
          '/use-cases',
          '/compare',
          '/docs',
        ],
        disallow: [
          '/api/',
          '/login',
          '/calendario',
          '/content-hub',
          '/ricerca',
          '/metriche',
          '/memory',
          '/writing-lab',
          '/brands',
          '/deep-research',
          '/blog-manager',
          '/social',
          '/videos',
          '/costi-api',
          '/competitor-watch',
          '/settings',
          '/setup',
          '/newsletter',
          '/revenue',
        ],
      },
    ],
    sitemap: `${process.env.NEXT_PUBLIC_SITE_URL || 'https://zerohuman.vercel.app'}/sitemap.xml`,
  }
}
