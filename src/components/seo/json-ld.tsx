/**
 * JSON-LD structured data for search engines and AI models.
 * Renders Organization + SoftwareApplication schema.
 *
 * Usage: drop <JsonLd /> into any layout that should carry structured data.
 */

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://zerohuman.vercel.app'

const organizationSchema = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'ZeroHuman',
  url: SITE_URL,
  logo: `${SITE_URL}/brand/zerohuman-mark-512.png`,
  sameAs: ['https://github.com/davidesilver/ZeroHuman-Agency'],
  description:
    'Open-source AI content operations platform for agencies and teams.',
}

const softwareSchema = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'ZeroHuman Content Engine',
  applicationCategory: 'BusinessApplication',
  operatingSystem: 'Cross-platform (Docker, Node.js)',
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'USD',
  },
  url: SITE_URL,
  downloadUrl: 'https://github.com/davidesilver/ZeroHuman-Agency',
  softwareVersion: '0.1.0',
  license: 'https://opensource.org/licenses/MIT',
  description:
    'Autonomous AI content operations — research, draft, multi-agent review, humanize, and publish across every brand. Self-hosted, multi-tenant, MIT licensed.',
  featureList: [
    'AI content research pipeline with 10+ retrievers',
    'Multi-dimensional content scoring',
    'Platform-native draft generation (LinkedIn, Twitter, blog, newsletter)',
    '4-agent GOD Mode review (critic, fact-checker, creative, synthesis)',
    'Content humanizer with brand voice application',
    'Writing Lab challenger/champion rounds',
    'Native multi-tenancy with per-brand data isolation',
    'Social publishing via Postiz',
    'Newsletter composition and multi-provider delivery',
    'Deep research via Docker sidecar',
    'Competitor content monitoring',
    'AI image generation',
    'Performance feedback loop',
    'LLM cost tracking and observability',
  ],
}

export function JsonLd() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(organizationSchema),
        }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(softwareSchema),
        }}
      />
    </>
  )
}
