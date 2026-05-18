import { Html, Head, Body, Container, Section, Text, Heading, Hr } from '@react-email/components'
import { EmailHeader, EmailFooter, SectionBlock } from './shared'
import type { BrandTheme, EmailContent } from './types'

interface Props {
  content: EmailContent
  theme: BrandTheme
}

export function DigestLayout({ content, theme }: Props) {
  return (
    <Html lang="en">
      <Head />
      <Body style={{ margin: '0', padding: '0', backgroundColor: '#f5f5f5', fontFamily: theme.fontFamily }}>
        <Container style={{ maxWidth: '600px', margin: '0 auto', backgroundColor: '#ffffff' }}>
          <EmailHeader theme={theme} editionNumber={content.editionNumber} />

          <Section style={{ padding: '24px' }}>
            {/* Intro */}
            {content.intro && (
              <Section style={{ marginBottom: '24px', paddingBottom: '24px', borderBottom: '2px solid ' + theme.accentColor }}>
                <Heading
                  as="h2"
                  style={{ fontSize: '22px', margin: '0 0 12px', color: '#1a1a1a', fontFamily: theme.fontFamily }}
                >
                  {content.title}
                </Heading>
                <Text style={{ fontSize: '15px', lineHeight: '1.7', color: '#555', margin: '0', fontFamily: theme.fontFamily }}>
                  {content.intro}
                </Text>
              </Section>
            )}

            {/* Sections */}
            {content.sections.map((section, i) => (
              <SectionBlock key={i} section={section} theme={theme} />
            ))}

            {/* Closing */}
            {content.closing && (
              <Section style={{ paddingTop: '16px' }}>
                <Text style={{ fontSize: '14px', lineHeight: '1.6', color: '#666', fontStyle: 'italic', margin: '0', fontFamily: theme.fontFamily }}>
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
