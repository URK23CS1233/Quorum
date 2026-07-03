import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/", "/auth/login", "/auth/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths and API routes
  if (
    PUBLIC_PATHS.some(p => pathname === p) ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // Dashboard routes need auth — checked client-side via AuthGuard
  // Middleware here is lightweight; token validation happens in the component
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
