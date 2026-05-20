import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

// Public paths that bypass authentication (marketing site, SEO assets).
const PUBLIC_PREFIXES = [
  '/features',
  '/blog',
  '/use-cases',
  '/compare',
  '/docs',
]

function isPublicPath(pathname: string): boolean {
  if (pathname === '/') return true
  return PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))
}

// Paths that bypass the bootstrap redirect even without Supabase configured
const BOOTSTRAP_EXEMPT = ['/bootstrap', '/api/bootstrap']

export async function updateSession(request: NextRequest) {
  const { pathname } = request.nextUrl

  // If Supabase is not configured, redirect everything to /bootstrap
  // (except the bootstrap page itself and its API routes)
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!supabaseUrl || !supabaseKey) {
    const isExempt = BOOTSTRAP_EXEMPT.some(p => pathname.startsWith(p))
    if (!isExempt) {
      const url = request.nextUrl.clone()
      url.pathname = '/bootstrap'
      return NextResponse.redirect(url)
    }
    return NextResponse.next({ request })
  }

  let supabaseResponse = NextResponse.next({ request })

  // Skip Supabase session refresh for public pages — avoids an unnecessary
  // round-trip to the auth server on every marketing page load.
  if (isPublicPath(request.nextUrl.pathname)) {
    return supabaseResponse
  }

  const supabase = createServerClient(
    supabaseUrl,
    supabaseKey,
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
