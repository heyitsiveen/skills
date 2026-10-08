"""The processes the program started, looked at and stopped by their pid, never by name.

Every look goes through `ps -ww`, which prints a whole command line: without it
some Linux builds cut a piped line at 80 columns, and the path a check looks for
falls off the end.
"""

import os
import signal
import subprocess
import time


def field(pid, name):
    """One `ps` field of `pid` (stat, lstart, command …), or "" when no such process runs."""
    try:
        return subprocess.run(["ps", "-ww", "-o", name + "=", "-p", str(pid)],
                              stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def alive(pid):
    """True while `pid` runs: a zombie waiting for its parent does not."""
    state = field(pid, "stat")
    return bool(state) and not state.startswith("Z")


def runs(pid, binary):
    """True while `pid` runs `binary`, as its whole command line names it."""
    return bool(binary) and alive(pid) and binary in field(pid, "command")


def kill_group(pid):
    """Kill the process group `pid` leads; False when there is none."""
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        return False
    return True


def stop_recorded(pid_file, binary, wait=10):
    """Stop the Chrome a profile's pid file names, by its process group, while that pid still
    runs `binary`: its pid, or None when there was nothing of the invocation's to stop."""
    try:
        with open(pid_file, encoding="utf-8") as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    if not runs(pid, binary) or not kill_group(pid):
        return None
    deadline = time.monotonic() + wait
    while alive(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    return pid


def listing():
    """[(pid, command)] of every process on the machine."""
    try:
        out = subprocess.run(["ps", "-A", "-ww", "-o", "pid=", "-o", "command="],
                             stdin=subprocess.DEVNULL, capture_output=True, text=True,
                             timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    found = []
    for line in out.splitlines():
        pid, _, command = line.strip().partition(" ")
        if pid.isdigit():
            found.append((int(pid), command.strip()))
    return found
