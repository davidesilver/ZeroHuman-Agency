/**
 * Bootstrap layout — shown when Supabase is not configured.
 * No auth, no Supabase client, no dashboard shell. Purely static.
 */
export default function BootstrapLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0f0f0f] text-[#f5f0e8] flex flex-col items-center justify-center px-4 font-sans antialiased">
        {children}
      </body>
    </html>
  )
}
