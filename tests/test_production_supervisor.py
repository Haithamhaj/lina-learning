from __future__ import annotations

import sys

from scripts.production_supervisor import ChildSpec, ProcessSupervisor, production_children


def test_production_topology_has_only_public_next_and_private_api() -> None:
    children = {child.name: child for child in production_children()}

    assert set(children) == {"next", "api", "worker"}
    assert children["next"].command[-1] == "start"
    assert children["api"].command[children["api"].command.index("--host") + 1] == "127.0.0.1"
    assert children["api"].command[children["api"].command.index("--port") + 1] == "8000"
    assert "--reload" not in children["api"].command
    assert "--reload" not in children["worker"].command


def test_supervisor_exits_and_terminates_peers_when_a_required_process_exits() -> None:
    immediate_exit = ChildSpec("broken", (sys.executable, "-c", "raise SystemExit(23)"))
    long_lived = ChildSpec("peer", (sys.executable, "-c", "import time; time.sleep(30)"))
    supervisor = ProcessSupervisor(
        children=(immediate_exit, long_lived),
        shutdown_grace_seconds=1,
    )

    assert supervisor.run() == 23
