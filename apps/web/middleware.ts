import { clerkMiddleware } from "@clerk/nextjs/server";

/**
 * Auth surface for the web app.
 *
 * Keep Clerk edge middleware out of product pages on Vercel. Auth state is
 * handled client-side with Clerk hooks/components; API proxy routes also skip
 * middleware so SSE streaming can reach the Railway backend untouched.
 */
export default clerkMiddleware();

export const config = {
  matcher: ["/__clerk/(.*)"],
};
