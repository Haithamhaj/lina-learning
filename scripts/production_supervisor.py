"""Run Lina's long-lived container processes as one unit on Cloud Run."""

from __future__ import annotations

import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from types import FrameType
from typing import Any, Callable, Mapping, Sequence


_LOG = logging.getLogger("lina.production")


@dataclass(frozen=True)
class ChildSpec:
    name: str
    command: tuple[str, ...]
    environment: Mapping[str, str] = field(default_factory=dict)


def production_children() -> tuple[ChildSpec, ...]:
    python = os.environ.get("LINA_PRODUCTION_PYTHON", ".venv-production/bin/python")
    port = os.environ.get("PORT", "5000")
    next_environment = {"HOSTNAME": "0.0.0.0", "PORT": port}
    if clerk_publishable_key := os.environ.get("CLERK_PUBLISHABLE_KEY"):
        next_environment["NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"] = clerk_publishable_key

    children: list[ChildSpec] = [
        ChildSpec("api", (python, "-u", "-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", "8000")),
        ChildSpec(
            "next",
            ("node", "apps/web/.next/standalone/apps/web/server.js"),
            next_environment,
        ),
    ]

    enable_worker = os.environ.get("LINA_ENABLE_WORKER", "true").lower() not in {"false", "0", "no", "off"}
    if enable_worker:
        children.append(ChildSpec("worker", (python, "-m", "workers.job_worker")))

    return tuple(children)


@dataclass
class ProcessSupervisor:
    """Terminate the whole deployment if any required process exits.

    Cloud Run owns container-level restart policy. Treating a child exit as fatal keeps a
    broken API or worker visible instead of silently serving a partial system.
    """

    children: Sequence[ChildSpec] = field(default_factory=production_children)
    shutdown_grace_seconds: float = 10.0
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen
    sleep: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if not self.children:
            raise ValueError("at least one child process is required")
        self._processes: list[subprocess.Popen[bytes]] = []
        self._shutdown_requested = False

    def run(self) -> int:
        previous = self._install_signal_handlers()
        try:
            for child in self.children:
                if child.name == "next" and any(c.name == "api" for c in self.children):
                    _LOG.info("Waiting for FastAPI (127.0.0.1:8000) before starting Next.js...")
                    deadline = time.monotonic() + 60.0
                    api_ready = False
                    while time.monotonic() < deadline and not self._shutdown_requested:
                        try:
                            with socket.create_connection(("127.0.0.1", 8000), timeout=0.5):
                                api_ready = True
                                break
                        except (OSError, ConnectionRefusedError):
                            time.sleep(0.3)
                    if api_ready:
                        _LOG.info("FastAPI is ready and listening on 127.0.0.1:8000!")
                    else:
                        _LOG.warning("FastAPI startup timeout reached; proceeding with Next.js...")

                _LOG.info("Starting %s: %s", child.name, " ".join(child.command))
                environment = os.environ.copy()
                environment.update(child.environment)
                environment["PYTHONPATH"] = os.getcwd()
                environment["PYTHONUNBUFFERED"] = "1"
                process = self.popen(
                    list(child.command),
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                self._processes.append(process)
                if process.stdout is not None:
                    thread = threading.Thread(
                        target=self._stream_logs,
                        args=(child.name, process.stdout),
                        daemon=True,
                    )
                    thread.start()
            while not self._shutdown_requested:
                for child, process in zip(self.children, self._processes, strict=True):
                    if (code := process.poll()) is not None:
                        _LOG.error("Required process %s exited with status %s", child.name, code)
                        return abs(code) if code else 1
                self.sleep(0.1)
            return 0
        except OSError:
            _LOG.exception("Unable to start required production process")
            return 1
        finally:
            self._shutdown()
            self._restore_signal_handlers(previous)

    @staticmethod
    def _stream_logs(name: str, stream: Any) -> None:
        try:
            for line in iter(stream.readline, b""):
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    _LOG.info("[%s] %s", name, text)
        except Exception:
            pass
        finally:
            stream.close()

    def request_shutdown(self, _signum: int, _frame: FrameType | None) -> None:
        self._shutdown_requested = True

    def _shutdown(self) -> None:
        for process in self._processes:
            if process.poll() is None:
                self._signal_group(process, signal.SIGTERM)
        deadline = time.monotonic() + self.shutdown_grace_seconds
        while time.monotonic() < deadline and any(process.poll() is None for process in self._processes):
            self.sleep(0.1)
        for process in self._processes:
            if process.poll() is None:
                self._signal_group(process, signal.SIGKILL)

    @staticmethod
    def _signal_group(process: subprocess.Popen[bytes], signum: signal.Signals) -> None:
        try:
            if process.pid is not None:
                os.killpg(process.pid, signum)
        except ProcessLookupError:
            pass

    def _install_signal_handlers(self) -> dict[int, signal.Handlers]:
        previous = {signum: signal.getsignal(signum) for signum in (signal.SIGTERM, signal.SIGINT)}
        for signum in previous:
            signal.signal(signum, self.request_shutdown)
        return previous

    @staticmethod
    def _restore_signal_handlers(previous: dict[int, signal.Handlers]) -> None:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
    sys.exit(ProcessSupervisor().run())
