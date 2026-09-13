"""Fail the production build if the API or persistent worker cannot import."""

from importlib import import_module


def main() -> None:
    for module_name in ("apps.api.main", "workers.job_worker"):
        import_module(module_name)


if __name__ == "__main__":
    main()
