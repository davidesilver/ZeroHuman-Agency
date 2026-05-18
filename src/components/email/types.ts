export interface BrandTheme {
  primaryColor: string    // hex, e.g. '#1a1a1a'
  accentColor: string     // hex, e.g. '#2e7d32'
  fontFamily: string      // CSS font stack
  logoUrl?: string        // absolute URL or empty
  brandName: string
}

export interface EmailSection {
  label: string
  title: string
  body: string
  ctaText?: string
  ctaUrl?: string
  sourceUrl?: string
}

export interface EmailContent {
  title: string
  intro?: string
  sections: EmailSection[]
  closing?: string
  editionNumber?: number
  unsubscribeUrl?: string
}

export const DEFAULT_THEME: BrandTheme = {
  primaryColor: '#1a1a1a',
  accentColor: '#2563eb',
  fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  brandName: 'Newsletter',
}
