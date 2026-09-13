import { clerkMiddleware } from "@clerk/nextjs/server";

export default clerkMiddleware({
  proxyUrl: process.env.NEXT_PUBLIC_LINA_CLERK_PROXY_PATH || undefined,
});

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)"],
};