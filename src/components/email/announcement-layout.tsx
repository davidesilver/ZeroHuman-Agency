import { Html, Head, Body, Container, Section, Text, Heading, Link } from '@react-email/components'
import { EmailHeader, EmailFooter } from './shared'
import type { BrandTheme, EmailContent } from './types'

interface Props {
  content: EmailContent
  theme: BrandTheme
}

export function AnnouncementLayout({ content, theme }: Props) {
  const main = content.sections[0]

  return (
    <Html lang="en">
      <Head />
      <Body style={{ margin: '0', padding: '0', backgroundColor: '#f5f5f5', fontFamily: theme.fontFamily }}>
        <Container style={{ maxWidth: '600px', margin: '0 auto', backgroundColor: '#ffffff' }}>
          <EmailHeader theme={theme} editionNumber={content.editionNumber} />

          {/* Announcement hero */}
          <Section style={{ padding: '40px 32px', textAlign: 'center', backgroundColor: '#fff' }}>
            {main?.label && (
              <Text
                style={{
                  display: 'inline-block',
                  backgroundColor: theme.accentColor,
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: '700',
                  padding: '4px 12px',
                  borderRadius: '20px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  marginBottom: '16px',
                  fontFamily: theme.fontFamily,
                }}
              >
                {main.label}
              </Text>
            )}
            <Heading
              as="h1"
              style={{
                fontSize: '28px',
                margin: '0 0 16px',
                color: '#1a1a1a',
                lineHeight: '1.25',
                fontFamily: theme.fontFamily,
              }}
            >
              {content.title}
            </Heading>
            {content.intro && (
              <Text style={{ fontSize: '16px', lineHeight: '1.7', color: '#555', margin: '0 0 24px', fontFamily: theme.fontFamily }}>
                {content.intro}
              </Text>
            )}
            {main?.body && (
              <Text style={{ fontSize: '15px', lineHeight: '1.7', color: '#444', margin: '0 0 28px', fontFamily: theme.fontFamily }}>
                {main.body}
              </Text>
            )}
            {/* Primary CTA */}
            {main?.ctaText && main?.ctaUrl ? (
              <Link
                href={main.ctaUrl}
                style={{
                  display: 'inline-block',
                  backgroundColor: theme.accentColor,
                  color: '#ffffff',
                  padding: '14px 32px',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: '700',
                  textDecoration: 'none',
                  fontFamily: theme.fontFamily,
                }}
              >
                {main.ctaText}
              </Link>
            ) : null}
          </Section>

          {/* Extra sections (if any) */}
          {content.sections.slice(1).map((section, i) => (
            <Section
              key={i}
              style={{
                padding: '16px 32px',
                borderTop: '1px solid #eee',
                backgroundColor: i % 2 === 0 ? '#fafafa' : '#fff',
              }}
            >
              {section.title && (
                <Text style={{ fontSize: '14px', fontWeight: '600', color: '#1a1a1a', margin: '0 0 4px', fontFamily: theme.fontFamily }}>
                  {section.title}
                </Text>
              )}
              <Text style={{ fontSize: '13px', lineHeight: '1.6', color: '#666', margin: '0', fontFamily: theme.fontFamily }}>
                {section.body}
              </Text>
            </Section>
          ))}

          {content.closing && (
            <Section style={{ padding: '20px 32px', textAlign: 'center' }}>
              <Text style={{ fontSize: '13px', color: '#888', fontStyle: 'italic', margin: '0', fontFamily: theme.fontFamily }}>
                {content.closing}
              </Text>
            </Section>
          )}

          <EmailFooter theme={theme} unsubscribeUrl={content.unsubscribeUrl} />
        </Container>
      </Body>
    </Html>
  )
}
