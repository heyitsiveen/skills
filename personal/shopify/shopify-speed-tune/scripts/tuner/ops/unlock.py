"""unlock: clear the machine lock an abandoned invocation left behind.

Only the developer knows an invocation is abandoned, so the lock is cleared
only when it is named by id. `finish`, run from the invocation's repo, is the
better ending whenever it can still run: it also deletes the Control theme and
removes Chrome. `unlock` frees the machine, stops the `caffeinate` that kept it
awake, and lists what is left to tidy.
"""

import os

from tuner import awake, ledger, lock
from tuner.output import Refused, note, say

ORDER = 95


def register(sub):
    p = sub.add_parser("unlock", help="clear the lock of an abandoned invocation, named by id")
    p.add_argument("--invocation", required=True,
                   help="the abandoned invocation's id, as the refused start names it")
    p.set_defaults(run=run)


def run(args):
    held = lock.read()
    if held is None:
        say("UNLOCK", "nothing to release: no invocation holds the lock")
        return 0
    if held.get("invocation") != args.invocation:
        raise Refused("wrong-invocation", "the lock belongs to %s, not %s"
                      % (lock.describe(held), args.invocation))
    lock.release(args.invocation)
    say("UNLOCK", "released %s" % args.invocation, "store=%s" % held.get("store"),
        "repo=%s" % held.get("repo"))

    folder = os.path.dirname(held.get("ledger", ""))
    try:
        inv = ledger.load(folder)
    except (OSError, ValueError):
        note("its ledger at %s is unreadable; check the store's theme library by hand"
             % held.get("ledger"))
        inv = None
    # The ledger's record, which says whether `finish` already stopped it; the
    # lock's copy when the ledger cannot be read.
    if awake.release((inv.data.get("awake") if inv is not None else None) or held.get("awake")):
        say("UNLOCK", "awake released")
    if inv is not None and inv.data.get("awake"):
        inv.save()
    if inv is not None and inv.data.get("state") == "open":
        inv.data["state"] = "abandoned"
        inv.log("unlock", "lock cleared by the developer; invocation abandoned")
        inv.save()
        for role, theme in sorted(inv.data.get("themes", {}).items()):
            if not theme.get("deleted"):
                note("%s theme %s (%s) may still be in the theme library"
                     % (role, theme.get("id"), theme.get("name")))
    workspace = held.get("workspace")
    if workspace and os.path.isdir(workspace):
        note("its temp workspace (Chrome, pnpm store) is still at %s" % workspace)
    return 0
