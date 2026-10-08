"""The machine lock: at most one unfinished invocation per machine.

Two invocations on one Mac share its CPU, and every Sample either takes is then
measured against the other's load. `start` takes the lock and `finish` releases
it. An invocation spans many processes, so nothing here is tied to a pid: a lock
whose invocation was abandoned stays until `unlock` names it.

The lock lives in the user's cache folder, outside every session's temp dir, so
two Claude sessions see the same lock. SPEED_TUNE_LOCK moves it (tests do).
"""

import json
import os
import sys
from datetime import datetime

from tuner.output import Refused


def path():
    override = os.environ.get("SPEED_TUNE_LOCK")
    if override:
        return override
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Caches")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "shopify-speed-tune.lock")


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read():
    try:
        with open(path(), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {"invocation": "unreadable"}


def describe(held):
    return "invocation %s for %s in %s, started %s, last operation %s at %s" % (
        held.get("invocation"), held.get("store"), held.get("repo"), held.get("started_at"),
        held.get("last_op", "?"), held.get("last_op_at", "?"))


def refuse_if_held():
    held = read()
    if held is not None:
        raise Refused(
            "invocation-unfinished", describe(held),
            "Finish it with `finish` from its repo. If it was abandoned, clear the lock "
            "with `unlock --invocation %s`." % held.get("invocation"))


def acquire(info):
    target = path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    record = dict(info, started_at=now(), last_op="start", last_op_at=now())
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        refuse_if_held()
        raise
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)


def touch(invocation, op):
    update(invocation, last_op=op, last_op_at=now())


def update(invocation, **fields):
    """Add `fields` to the lock, while `invocation` holds it."""
    held = read()
    if not held or held.get("invocation") != invocation:
        return
    held.update(fields)
    tmp = path() + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        json.dump(held, f, indent=2)
    os.replace(tmp, path())


def release(invocation):
    held = read()
    if held and held.get("invocation") == invocation:
        os.remove(path())
        return True
    return False
