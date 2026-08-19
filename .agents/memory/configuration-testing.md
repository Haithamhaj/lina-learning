---
name: Configuration testing in Replit
description: Environment values provided by the workspace can affect tests for missing configuration.
---

Tests for missing production configuration must explicitly remove relevant
environment variables before constructing settings.

**Why:** The Replit runtime can provide server secrets and deployment values to
the test process, so a “missing variable” test may pass unexpectedly unless it
isolates the environment.

**How to apply:** Use pytest's `monkeypatch.delenv` for every required setting
under test, then instantiate the settings object with `.env` loading disabled.