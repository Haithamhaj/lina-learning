from __future__ import annotations

import sys

from scripts.production_supervisor import ChildSpec, ProcessSupervisor, production_children


def test_reserved_vm_topology_has_one_public_web_process() -> None:
    children = {child.name: child for child in production_children()}

    assert set(children) == {"next", "api", "worker"}
    assert children["next"].command[-1] == "start"
    assert "--reload" not in children["api"].command
    assert "--reload" not in children["worker"].command
    assert children["api"].command[children["api"].command.index("--port") + 1] == "8000"
    assert children["api"].command[children["api"].command.index("--host") + 1] == "127.0.0.1"


def test_startup_failure_is_propagated_without_restart() -> None:
    child = ChildSpec(
        "broken",
        (sys.executable, "-c", "raise SystemExit(23)"),
    )
    supervisor = ProcessSupervisor(
        children=(child,),
        startup_grace_seconds=1,
        shutdown_grace_seconds=0,
    )

    assert supervisor.run() == 23


def test_post_start_failure_restarts_with_a_bound_attempt_count(tmp_path) -> None:
    marker = repr(str(tmp_path / "starts"))
    command = (
        "from pathlib import Path; import os, signal, time; "
        f"marker = Path({marker}); "
        "count = int(marker.read_text()) if marker.exists() else 0; "
        "marker.write_text(str(count + 1))\n"
        "if count == 0: raise SystemExit(9)\n"
        "os.kill(os.getppid(), signal.SIGTERM); time.sleep(30)"
    )
    supervisor = ProcessSupervisor(
        children=(ChildSpec("restartable", (sys.executable, "-c", command)),),
        startup_grace_seconds=0,
        restart_limit=2,
        restart_backoff_seconds=0.01,
        max_restart_backoff_seconds=0.01,
        shutdown_grace_seconds=2,
    )

    assert supervisor.run() == 0
    assert (tmp_path / "starts").read_text() == "2"


def test_signal_requests_clean_shutdown() -> None:
    child = ChildSpec(
        "long-lived",
        (
            sys.executable,
            "-c",
            (
                "import os, signal, time; "
                "os.kill(os.getppid(), signal.SIGTERM); time.sleep(30)"
            ),
        ),
    )
    supervisor = ProcessSupervisor(
        children=(child,),
        startup_grace_seconds=0,
        shutdown_grace_seconds=2,
    )

    assert supervisor.run() == 0