import { clerkMiddleware } from "@clerk/nextjs/server";

export default clerkMiddleware({
  proxyUrl: process.env.CLERK_PROXY_URL,
});

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)"],
};