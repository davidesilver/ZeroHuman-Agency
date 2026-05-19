import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

// Public paths that bypass authentication (marketing site, SEO assets).
// Next.js route groups like (marketing) don't appear in the URL, so we
// match on the actual path segments served to users.
const PUBLIC_PREFIXES = [
  '/features',
  '/blog',
  '/use-cases',
  '/compare',
  '/docs',
]

function isPublicPath(pathname: string): boolean {
  // Root "/" will be the marketing landing page once the (marketing) route group exists.
  // Until then the dashboard layout handles its own auth redirect, so letting
  // "/" through here is safe — unauthenticated users hitting the dashboard layout
  // are redirected to /login by its server-side check.
  if (pathname === '/') return true
  return PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))
}

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  // Skip Supabase session refresh for public pages — avoids an unnecessary
  // round-trip to the auth server on every marketing page load.
  if (isPublicPath(request.nextUrl.pathname)) {
    return supabaseResponse
  }

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          )
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user && !request.nextUrl.pathname.startsWith('/login')) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  if (user && request.nextUrl.pathname.startsWith('/login')) {
    const url = request.nextUrl.clone()
    url.pathname = '/'
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}
