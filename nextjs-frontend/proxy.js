import { NextResponse } from 'next/server';

export function proxy(request) {
  const token = request.cookies.get('access_token');
  const isAuthPage = request.nextUrl.pathname.startsWith('/auth');

  // If the user is unauthenticated and trying to access protected routes
  if (!token) {
    if (!isAuthPage) {
      // Redirect to login page
      return NextResponse.redirect(new URL('/auth', request.url));
    }
  } else {
    // If the user IS authenticated and trying to access /auth, redirect to dashboard
    if (isAuthPage) {
      // Basic heuristic, could get smarter by parsing JWT or user cookie
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
  }

  return NextResponse.next();
}

// See "Matching Paths" below to learn more
export const config = {
  matcher: [
    '/dashboard/:path*',
    '/helper-dashboard/:path*',
    '/connections/:path*',
    '/messages/:path*',
    '/inquiry/:path*', 
    '/auth/:path*' // We handle auth specifically above
  ]
};
