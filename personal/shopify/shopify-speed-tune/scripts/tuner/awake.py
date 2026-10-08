"""Keeping the Mac awake while an invocation runs.

On battery a Mac sleeps after a few idle minutes, even in the middle of a
Measurement, and the Rounds run unattended for hours. `start` therefore holds
one `caffeinate -i` (no idle sleep) for the whole invocation, and records its
pid with the time it started. `finish` and `unlock` stop it by that pid, and
only while the pid still names the process `start` started, so a pid the
system has since given to another program is never signalled. Where there is
no `caffeinate` (not a Mac), nothing is held.
"""

import os
import shutil
import signal
import subprocess
import time


def _ps(field, pid):
    try:
        proc = subprocess.run(["ps", "-o", field + "=", "-p", str(pid)], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout.strip()


def _alive(pid):
    state = _ps("stat", pid)
    return bool(state) and not state.startswith("Z")


def hold():
    """Start the invocation's `caffeinate -i`: {pid, started}, or None without one."""
    binary = shutil.which("caffeinate")
    if binary is None:
        return None
    try:
        proc = subprocess.Popen([binary, "-i"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return None
    started = _ps("lstart", proc.pid)
    if not started:
        return None
    return {"pid": proc.pid, "started": started}


def running(held):
    """True while the process `hold` started still runs."""
    return bool(held) and _alive(held["pid"]) and _ps("lstart", held["pid"]) == held["started"]


def release(held):
    """Stop the held process by its pid; True when this call stopped it."""
    if not held or held.get("released"):
        return False
    pid = held["pid"]
    if not _alive(pid) or _ps("lstart", pid) != held["started"]:
        held["released"] = "already gone"
        return False
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 5
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    if _alive(pid) and _ps("lstart", pid) == held["started"]:
        os.kill(pid, signal.SIGKILL)
    held["released"] = "stopped"
    return True
