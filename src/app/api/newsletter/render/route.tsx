import { NextRequest, NextResponse } from 'next/server'
import { render } from '@react-email/render'
import { DigestLayout } from '@/components/email/digest-layout'
import { SingleStoryLayout } from '@/components/email/single-story-layout'
import { AnnouncementLayout } from '@/components/email/announcement-layout'
import { DEFAULT_THEME } from '@/components/email/types'
import type { BrandTheme, EmailContent } from '@/components/email/types'

const LAYOUTS = {
  digest: DigestLayout,
  single_story: SingleStoryLayout,
  announcement: AnnouncementLayout,
} as const

type LayoutKey = keyof typeof LAYOUTS

// Extracted so JSX is not constructed inside a try/catch block
async function renderLayout(Layout: (typeof LAYOUTS)[LayoutKey], content: EmailContent, theme: BrandTheme) {
  const html = await render(<Layout content={content} theme={theme} />)
  return NextResponse.json({ html })
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const {
      layout = 'digest',
      content,
      brand_theme,
    }: {
      layout: string
      content: EmailContent
      brand_theme?: Partial<BrandTheme>
    } = body

    if (!content || !Array.isArray(content.sections)) {
      return NextResponse.json({ error: 'content.sections is required' }, { status: 400 })
    }

    const layoutKey = layout as LayoutKey
    if (!(layoutKey in LAYOUTS)) {
      return NextResponse.json(
        { error: `Unknown layout '${layout}'. Valid: ${Object.keys(LAYOUTS).join(', ')}` },
        { status: 400 },
      )
    }

    const theme: BrandTheme = { ...DEFAULT_THEME, ...brand_theme }
    const Layout = LAYOUTS[layoutKey]
    return renderLayout(Layout, content, theme)
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Render failed'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
