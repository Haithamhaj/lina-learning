"""Fail the deployment build if API or worker dependencies are unavailable."""

from __future__ import annotations

import importlib


def main() -> None:
    for module_name in ("apps.api.main", "workers.job_worker"):
        importlib.import_module(module_name)
    print("Python production runtime dependencies are ready.")


if __name__ == "__main__":
    main()