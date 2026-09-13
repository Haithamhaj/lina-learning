---
name: Python deployment image size
description: Keeping Reserved VM images below platform limits when Python ML dependencies are required at runtime.
---

When runtime Python packages must be persisted from build into a Reserved VM image, constrain ML frameworks to CPU-only wheels and clear the package-manager cache after the persistent environment is complete.

**Why:** A default PyTorch resolution added CUDA/NVIDIA libraries, and uv retained duplicate package archives. The combined deployment layers exceeded the 8 GiB image limit even though the application itself was much smaller.

**How to apply:** Build a persistent production environment, validate imports from that environment, then clear uv's cache as the final Python build step. Confirm no GPU packages remain and measure both the environment and cache before publishing.