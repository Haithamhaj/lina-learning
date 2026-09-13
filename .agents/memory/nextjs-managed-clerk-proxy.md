---
name: Next.js managed Clerk proxy
description: SSR-safe handling of Replit-managed Clerk's relative production proxy in a Next.js app.
---

Keep Replit-managed Clerk's production proxy same-origin. Do not turn its relative path into an absolute URL with `REPLIT_DOMAINS` during build, because that value can identify the development host. Prevent Clerk's conventional relative proxy environment variables from being auto-resolved during Next prerendering; pass a browser-resolved same-origin URL instead.

**Why:** Clerk's Next.js SDK may resolve conventional relative proxy variables during SSR and touch `window`. Converting the path at build time avoids that error but can permanently embed a development origin in the production client, causing CORS failures.

**How to apply:** Preserve the relative proxy path under an application-owned public build variable, resolve it against `window.location.origin` in the client, and provide a real production proxy endpoint. Next treats underscore-prefixed App Router folders as private; encode the underscores in the route directory when the public URL segment must begin with underscores.