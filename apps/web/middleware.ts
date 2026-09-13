import { clerkMiddleware } from "@clerk/nextjs/server";

export default clerkMiddleware({
  frontendApiProxy: {
    enabled: true,
    path: "/api/__clerk",
  },
});

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)", "/api/__clerk/:path*"],
};
