---
name: Private internal workflow ports
description: Preventing development workflow readiness checks from exposing production-internal service ports.
---

Console workflows for services that must remain private in production should not use a port readiness setting. Replit can regenerate a public port mapping when such a workflow starts, even after that mapping was removed manually.

**Why:** A FastAPI service intended to be loopback-only regained an external mapping because its development workflow waited on the same internal port.

**How to apply:** Use a console workflow without a port wait for private internal services. After stopping local production tests, verify the final deployment configuration exposes only the intended public web port.