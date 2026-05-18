import {
  Html, Head, Body, Container, Section, Text, Heading,
  Hr, Link, Img, Row, Column,
} from '@react-email/components'
import type { BrandTheme, EmailSection } from './types'

export { Html, Head, Body, Container, Section, Text, Heading, Hr, Link, Img, Row, Column }

export function EmailHeader({ theme, editionNumber }: { theme: BrandTheme; editionNumber?: number }) {
  return (
    <Section style={{ backgroundColor: theme.primaryColor, padding: '24px', textAlign: 'center' }}>
      {theme.logoUrl ? (
        <Img
          src={theme.logoUrl}
          alt={theme.brandName}
          width={120}
          height={40}
          style={{ display: 'block', margin: '0 auto 12px' }}
        />
      ) : (
        <Heading
          as="h1"
          style={{ color: '#ffffff', fontSize: '20px', margin: '0 0 4px', fontFamily: theme.fontFamily }}
        >
          {theme.brandName}
        </Heading>
      )}
      {editionNumber != null && (
        <Text style={{ color: '#888888', fontSize: '12px', margin: '0', fontFamily: theme.fontFamily }}>
          Edition #{editionNumber}
        </Text>
      )}
    </Section>
  )
}

export function EmailFooter({
  theme,
  unsubscribeUrl = '#unsubscribe',
}: {
  theme: BrandTheme
  unsubscribeUrl?: string
}) {
  return (
    <Section style={{ backgroundColor: '#f5f5f5', padding: '16px 24px', textAlign: 'center' }}>
      <Text style={{ color: '#999', fontSize: '11px', margin: '0 0 4px', fontFamily: theme.fontFamily }}>
        You received this because you subscribed to {theme.brandName}.
      </Text>
      <Link href={unsubscribeUrl} style={{ color: '#666', fontSize: '11px', fontFamily: theme.fontFamily }}>
        Unsubscribe
      </Link>
    </Section>
  )
}

export function SectionBlock({ section, theme }: { section: EmailSection; theme: BrandTheme }) {
  return (
    <Section style={{ marginBottom: '24px', paddingBottom: '24px', borderBottom: '1px solid #eeeeee' }}>
      {section.label && (
        <Text
          style={{
            display: 'inline-block',
            backgroundColor: theme.accentColor + '22',
            color: theme.accentColor,
            fontSize: '10px',
            fontWeight: '600',
            padding: '2px 8px',
            borderRadius: '4px',
            textTransform: 'uppercase',
            marginBottom: '8px',
            fontFamily: theme.fontFamily,
          }}
        >
          {section.label}
        </Text>
      )}
      {section.title && (
        <Heading
          as="h2"
          style={{ fontSize: '18px', margin: '0 0 8px', color: '#1a1a1a', fontFamily: theme.fontFamily }}
        >
          {section.title}
        </Heading>
      )}
      <Text style={{ fontSize: '14px', lineHeight: '1.6', color: '#444444', margin: '0', fontFamily: theme.fontFamily }}>
        {section.body}
      </Text>
      {section.ctaText && section.ctaUrl && (
        <Section style={{ marginTop: '12px' }}>
          <Link
            href={section.ctaUrl}
            style={{
              display: 'inline-block',
              backgroundColor: theme.accentColor,
              color: '#ffffff',
              padding: '8px 20px',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: '600',
              textDecoration: 'none',
              fontFamily: theme.fontFamily,
            }}
          >
            {section.ctaText}
          </Link>
        </Section>
      )}
    </Section>
  )
}
