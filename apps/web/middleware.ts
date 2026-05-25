import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

/**
 * Auth surface for the web app.
 *
 * Public routes (no Clerk session required):
 *   - `/`                  — landing page
 *   - `/sign-in/*`         — Clerk hosted sign-in
 *   - `/sign-up/*`         — Clerk hosted sign-up
 *   - `/api/*`             — proxied to the FastAPI backend; backend will
 *                            do its own auth via Clerk JWT verification.
 *                            (Putting auth.protect() here would break the
 *                            SSE chat stream because Clerk would intercept
 *                            it before it reaches FastAPI.)
 *
 * Everything else is private and requires a signed-in user. Visiting a
 * protected route while signed out redirects to `/sign-in`.
 */
const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
    "/__clerk/(.*)",
  ],
};
