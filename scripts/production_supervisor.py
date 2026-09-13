"""Supervise the three processes required by the Reserved VM deployment.

This intentionally stays a small, single-host supervisor instead of relying on
shell background jobs.  Each child gets its own process group, failures are
reported to the deployment process, and a bounded restart policy handles
transient post-start crashes without hiding a permanently broken deployment.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from types import FrameType
from typing import Callable, Mapping, Sequence


_logger = logging.getLogger("lina.production")
_POLL_INTERVAL_SECONDS = 0.1


@dataclass(frozen=True)
class ChildSpec:
    """A process that must remain alive for the deployment to be healthy."""

    name: str
    command: tuple[str, ...]
    env: Mapping[str, str] | None = None


@dataclass
class _ChildState:
    spec: ChildSpec
    process: subprocess.Popen[bytes] | None = None
    restart_count: int = 0
    restart_at: float = 0.0
    first_started_at: float | None = None
    started_at: float | None = None
    last_return_code: int | None = None


def production_children() -> tuple[ChildSpec, ...]:
    """Return the fixed production topology for one Reserved VM.

    Only Next is bound to the externally configured web port.  FastAPI is
    deliberately bound to loopback because Next proxies browser ``/api``
    requests to it.
    """

    uv = (
        "uv",
        "run",
        "--offline",
        "--with-requirements",
        "apps/api/requirements.txt",
    )
    return (
        ChildSpec(
            name="next",
            command=("npm", "--prefix", "apps/web", "run", "start"),
        ),
        ChildSpec(
            name="api",
            command=(
                *uv,
                "python",
                "-m",
                "uvicorn",
                "apps.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ),
        ),
        ChildSpec(
            name="worker",
            command=(
                *uv,
                "python",
                "-m",
                "workers.job_worker",
            ),
        ),
    )


@dataclass
class ProcessSupervisor:
    """Run and supervise a bounded set of long-lived child processes."""

    children: Sequence[ChildSpec] = field(default_factory=production_children)
    startup_grace_seconds: float = 10.0
    restart_limit: int = 5
    restart_backoff_seconds: float = 1.0
    max_restart_backoff_seconds: float = 30.0
    restart_reset_seconds: float = 300.0
    shutdown_grace_seconds: float = 10.0
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if not self.children:
            raise ValueError("at least one child process is required")
        if self.startup_grace_seconds < 0:
            raise ValueError("startup_grace_seconds must not be negative")
        if self.restart_limit < 0:
            raise ValueError("restart_limit must not be negative")
        if self.restart_backoff_seconds <= 0:
            raise ValueError("restart_backoff_seconds must be positive")
        if self.max_restart_backoff_seconds < self.restart_backoff_seconds:
            raise ValueError("max_restart_backoff_seconds must not be smaller than backoff")
        if self.restart_reset_seconds <= 0:
            raise ValueError("restart_reset_seconds must be positive")
        if self.shutdown_grace_seconds < 0:
            raise ValueError("shutdown_grace_seconds must not be negative")
        self._states = [_ChildState(child) for child in self.children]
        self._shutdown_requested = False
        self._signal_handlers_installed = False
        self._previous_signal_handlers: dict[int, signal.Handlers] = {}

    def run(self) -> int:
        """Run until shutdown or an unrecoverable child failure.

        A child that exits while the initial startup window is open is treated
        as a fatal startup error.  Once all children have survived that window,
        a bounded exponential restart policy handles crashes.  A restart limit
        is intentionally finite so deployment health cannot be falsely reported
        while a child is flapping.
        """

        try:
            self._install_signal_handlers()
            started_at = self.clock()
            for state in self._states:
                if self._shutdown_requested:
                    break
                self._start(state)

            while not self._shutdown_requested:
                now = self.clock()
                for state in self._states:
                    process = state.process
                    if process is not None:
                        return_code = process.poll()
                        if return_code is None:
                            if (
                                state.restart_count
                                and state.started_at is not None
                                and now - state.started_at >= self.restart_reset_seconds
                            ):
                                _logger.info(
                                    "%s remained stable; resetting restart count",
                                    state.spec.name,
                                )
                                state.restart_count = 0
                            continue
                        state.last_return_code = return_code
                        state.process = None
                        if now - started_at < self.startup_grace_seconds:
                            _logger.error(
                                "%s exited during startup with status %s",
                                state.spec.name,
                                return_code,
                            )
                            return self._fatal_exit_code(return_code)
                        if state.restart_count >= self.restart_limit:
                            _logger.error(
                                "%s exceeded the restart limit (%s), status %s",
                                state.spec.name,
                                self.restart_limit,
                                return_code,
                            )
                            return self._fatal_exit_code(return_code)
                        state.restart_count += 1
                        delay = min(
                            self.restart_backoff_seconds
                            * (2 ** (state.restart_count - 1)),
                            self.max_restart_backoff_seconds,
                        )
                        state.restart_at = now + delay
                        _logger.warning(
                            "%s exited with status %s; restarting in %.1fs "
                            "(attempt %s/%s)",
                            state.spec.name,
                            return_code,
                            delay,
                            state.restart_count,
                            self.restart_limit,
                        )

                    if (
                        state.process is None
                        and state.restart_at > 0
                        and now >= state.restart_at
                        and not self._shutdown_requested
                    ):
                        self._start(state)

                self.sleep(_POLL_INTERVAL_SECONDS)
        except (OSError, ValueError) as error:
            _logger.exception("Unable to start production process: %s", error)
            return 1
        finally:
            self._shutdown()
            self._restore_signal_handlers()

        return 0

    def request_shutdown(self, _signum: int | None = None, _frame: FrameType | None = None) -> None:
        """Mark shutdown requested; the supervisor loop performs the cleanup."""

        self._shutdown_requested = True

    def _start(self, state: _ChildState) -> None:
        environment = None
        if state.spec.env is not None:
            environment = os.environ.copy()
            environment.update(state.spec.env)
        _logger.info("Starting %s: %s", state.spec.name, " ".join(state.spec.command))
        state.process = self.popen(
            list(state.spec.command),
            env=environment,
            start_new_session=True,
        )
        state.started_at = self.clock()
        if state.first_started_at is None:
            state.first_started_at = state.started_at

    def _shutdown(self) -> None:
        processes = [state.process for state in self._states if state.process is not None]
        for process in processes:
            if process is not None and process.poll() is None:
                self._signal_process(process, signal.SIGTERM)

        deadline = self.clock() + self.shutdown_grace_seconds
        while self.clock() < deadline:
            live = [process for process in processes if process is not None and process.poll() is None]
            if not live:
                return
            self.sleep(min(_POLL_INTERVAL_SECONDS, max(0.0, deadline - self.clock())))

        for process in processes:
            if process is not None and process.poll() is None:
                self._signal_process(process, signal.SIGKILL)

    @staticmethod
    def _signal_process(process: subprocess.Popen[bytes], signum: signal.Signals) -> None:
        try:
            if process.pid is not None and hasattr(os, "killpg"):
                os.killpg(process.pid, signum)
            else:
                process.send_signal(signum)
        except ProcessLookupError:
            pass

    @staticmethod
    def _fatal_exit_code(return_code: int | None) -> int:
        if return_code is None or return_code == 0:
            return 1
        return abs(return_code)

    def _install_signal_handlers(self) -> None:
        if self._signal_handlers_installed:
            return
        self._previous_signal_handlers = {
            signal.SIGTERM: signal.getsignal(signal.SIGTERM),
            signal.SIGINT: signal.getsignal(signal.SIGINT),
        }
        signal.signal(signal.SIGTERM, self.request_shutdown)
        signal.signal(signal.SIGINT, self.request_shutdown)
        self._signal_handlers_installed = True

    def _restore_signal_handlers(self) -> None:
        if not self._signal_handlers_installed:
            return
        for signum, handler in self._previous_signal_handlers.items():
            signal.signal(signum, handler)
        self._previous_signal_handlers = {}
        self._signal_handlers_installed = False


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return ProcessSupervisor().run()


if __name__ == "__main__":
    sys.exit(main())