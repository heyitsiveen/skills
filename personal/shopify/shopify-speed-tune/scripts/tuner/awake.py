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

from tuner import processes


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
    started = processes.field(proc.pid, "lstart")
    if not started:
        return None
    return {"pid": proc.pid, "started": started}


def running(held):
    """True while the process `hold` started still runs: its pid, started when it was."""
    return bool(held) and processes.alive(held["pid"]) and \
        processes.field(held["pid"], "lstart") == held["started"]


def release(held):
    """Stop the held process by its pid; True when this call stopped it."""
    if not held or held.get("released"):
        return False
    if not running(held):
        held["released"] = "already gone"
        return False
    pid = held["pid"]
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 5
    while processes.alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    if running(held):
        os.kill(pid, signal.SIGKILL)
    held["released"] = "stopped"
    return True
