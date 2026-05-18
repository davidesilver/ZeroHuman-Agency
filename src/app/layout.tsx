import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Geist_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ZeroHuman — Content Engine",
  description: "Autonomous AI content operations — research, draft, review, publish across every brand.",
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
      lang="it"
      className={`${inter.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
