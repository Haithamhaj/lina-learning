import { clerkMiddleware } from "@clerk/nextjs/server";

export default clerkMiddleware({
  proxyUrl:
    process.env.NEXT_PUBLIC_CLERK_PROXY_URL ||
    process.env.CLERK_PROXY_URL ||
    undefined,
});

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)"],
};