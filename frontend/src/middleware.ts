import { NextRequest, NextResponse } from 'next/server'

/**
 * Proxy /api/*, /images/*, and /previews/* to the backend at runtime.
 *
 * BACKEND_URL is read here (server-side, at request time) rather than in
 * next.config.mjs rewrites(), which are evaluated at build time and would
 * bake in whatever value is present during `next build` — typically the
 * localhost fallback when building inside CI Docker.
 */
export function middleware(request: NextRequest) {
  const backendUrl = process.env.BACKEND_URL ?? 'http://localhost:8000'

  const { pathname, search } = request.nextUrl
  const destination = `${backendUrl}${pathname}${search}`

  return NextResponse.rewrite(destination)
}

export const config = {
  matcher: ['/api/:path*', '/images/:path*', '/previews/:path*'],
}
