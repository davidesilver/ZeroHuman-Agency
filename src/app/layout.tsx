import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Geist_Mono } from "next/font/google";
import { JsonLd } from "@/components/seo/json-ld";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://zerohuman.vercel.app'

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: 'ZeroHuman — Content Engine',
    template: '%s | ZeroHuman',
  },
  description:
    'Open-source AI content operations platform. Research, draft, review, and publish across every brand — with multi-agent review, humanizer, and full pipeline automation.',
  keywords: [
    'AI content automation',
    'content operations platform',
    'multi-agent content review',
    'AI content engine',
    'open source content platform',
    'multi-tenant content management',
    'AI brand voice',
    'content pipeline automation',
    'self-hosted AI content',
  ],
  authors: [{ name: 'ZeroHuman', url: SITE_URL }],
  creator: 'ZeroHuman',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: SITE_URL,
    siteName: 'ZeroHuman',
    title: 'ZeroHuman — Open-Source AI Content Engine',
    description:
      'Autonomous AI content operations — research, draft, review, publish across every brand. Multi-agent review, humanizer, self-hosted.',
    images: [
      {
        url: '/brand/zerohuman-logo-showcase.png',
        width: 1200,
        height: 630,
        alt: 'ZeroHuman Content Engine',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ZeroHuman — Open-Source AI Content Engine',
    description:
      'Autonomous AI content operations — research, draft, review, publish across every brand.',
    images: ['/brand/zerohuman-logo-showcase.png'],
  },
  icons: {
    icon: [
      { url: '/brand/zerohuman-mark-32.png', sizes: '32x32', type: 'image/png' },
      { url: '/brand/zerohuman-mark-64.png', sizes: '64x64', type: 'image/png' },
    ],
    apple: [
      { url: '/brand/zerohuman-mark-512.png', sizes: '512x512', type: 'image/png' },
    ],
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Note on hydration warnings for `bis_skin_checked="1"`:
  // Bitdefender's TrafficLight extension stamps that attribute on DOM nodes
  // during (and after) initial mount. React logs a dev-only hydration diff.
  // `suppressHydrationWarning` is intentionally set on <html>/<body> but does
  // not cascade to descendants — the warning therefore still surfaces for
  // deeper <div>s. This is harmless: production hydration is a one-shot
  // compare, and the extension mutation happens after React takes over.
  // Don't blanket-suppress descendants — that would mask real hydration bugs.
  return (
    <html
      lang="en"
      className={`${inter.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        {process.env.NODE_ENV === "development" && (
          <script
            suppressHydrationWarning
            dangerouslySetInnerHTML={{
              __html: `
                (function() {
                  const removeAttr = (el) => {
                    if (el && el.removeAttribute) {
                      if (el.hasAttribute('bis_skin_checked')) el.removeAttribute('bis_skin_checked');
                    }
                  };
                  
                  const walkAndRemove = (node) => {
                    if (node.nodeType === 1) {
                      removeAttr(node);
                      const children = node.getElementsByTagName('*');
                      for (let i = 0; i < children.length; i++) {
                        removeAttr(children[i]);
                      }
                    }
                  };

                  if (document.documentElement) {
                    walkAndRemove(document.documentElement);
                  }

                  const observer = new MutationObserver((mutations) => {
                    for (let i = 0; i < mutations.length; i++) {
                      const mutation = mutations[i];
                      if (mutation.type === 'attributes' && mutation.attributeName === 'bis_skin_checked') {
                        removeAttr(mutation.target);
                      } else if (mutation.type === 'childList') {
                        for (let j = 0; j < mutation.addedNodes.length; j++) {
                          walkAndRemove(mutation.addedNodes[j]);
                        }
                      }
                    }
                  });

                  observer.observe(document.documentElement, {
                    attributes: true,
                    childList: true,
                    subtree: true,
                    attributeFilter: ['bis_skin_checked']
                  });
                })();
              `,
            }}
          />
        )}
      </head>
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        <JsonLd />
        {children}
      </body>
    </html>
  );
}
