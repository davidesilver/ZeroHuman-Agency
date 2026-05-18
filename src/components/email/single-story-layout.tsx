import { Html, Head, Body, Container, Section, Text, Heading, Link } from '@react-email/components'
import { EmailHeader, EmailFooter } from './shared'
import type { BrandTheme, EmailContent } from './types'

interface Props {
  content: EmailContent
  theme: BrandTheme
}

export function SingleStoryLayout({ content, theme }: Props) {
  const main = content.sections[0]
  const rest = content.sections.slice(1)

  return (
    <Html lang="en">
      <Head />
      <Body style={{ margin: '0', padding: '0', backgroundColor: '#f5f5f5', fontFamily: theme.fontFamily }}>
        <Container style={{ maxWidth: '600px', margin: '0 auto', backgroundColor: '#ffffff' }}>
          <EmailHeader theme={theme} editionNumber={content.editionNumber} />

          {/* Hero */}
          <Section
            style={{
              backgroundColor: theme.accentColor + '11',
              borderLeft: `4px solid ${theme.accentColor}`,
              padding: '24px',
              margin: '0',
            }}
          >
            <Heading
              as="h1"
              style={{ fontSize: '26px', margin: '0 0 12px', color: '#1a1a1a', lineHeight: '1.3', fontFamily: theme.fontFamily }}
            >
              {content.title}
            </Heading>
            {content.intro && (
              <Text style={{ fontSize: '16px', lineHeight: '1.7', color: '#444', margin: '0', fontFamily: theme.fontFamily }}>
                {content.intro}
              </Text>
            )}
          </Section>

          <Section style={{ padding: '24px' }}>
            {/* Main story */}
            {main && (
              <Section style={{ marginBottom: '32px' }}>
                {main.label && (
                  <Text
                    style={{
                      fontSize: '11px',
                      fontWeight: '700',
                      textTransform: 'uppercase',
                      color: theme.accentColor,
                      letterSpacing: '0.1em',
                      margin: '0 0 8px',
                      fontFamily: theme.fontFamily,
                    }}
                  >
                    {main.label}
                  </Text>
                )}
                {main.title && (
                  <Heading
                    as="h2"
                    style={{ fontSize: '20px', margin: '0 0 12px', color: '#1a1a1a', fontFamily: theme.fontFamily }}
                  >
                    {main.title}
                  </Heading>
                )}
                <Text style={{ fontSize: '15px', lineHeight: '1.8', color: '#333', margin: '0', fontFamily: theme.fontFamily }}>
                  {main.body}
                </Text>
                {main.ctaText && main.ctaUrl && (
                  <Section style={{ marginTop: '16px' }}>
                    <Link
                      href={main.ctaUrl}
                      style={{
                        display: 'inline-block',
                        backgroundColor: theme.accentColor,
                        color: '#ffffff',
                        padding: '10px 24px',
                        borderRadius: '6px',
                        fontSize: '14px',
                        fontWeight: '600',
                        textDecoration: 'none',
                        fontFamily: theme.fontFamily,
                      }}
                    >
                      {main.ctaText}
                    </Link>
                  </Section>
                )}
              </Section>
            )}

            {/* Remaining sections (brief) */}
            {rest.map((section, i) => (
              <Section key={i} style={{ marginBottom: '16px', paddingTop: '16px', borderTop: '1px solid #eee' }}>
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
              <Section style={{ paddingTop: '20px', marginTop: '8px', borderTop: '2px solid ' + theme.accentColor }}>
                <Text style={{ fontSize: '14px', lineHeight: '1.6', color: '#555', fontStyle: 'italic', margin: '0', fontFamily: theme.fontFamily }}>
                  {content.closing}
                </Text>
              </Section>
            )}
          </Section>

          <EmailFooter theme={theme} unsubscribeUrl={content.unsubscribeUrl} />
        </Container>
      </Body>
    </Html>
  )
}
