"""finish: end the invocation, leaving only the Working theme and the branch.

Deletes the Control theme, puts the repo back on the branch the invocation
started from, restores Chrome for Testing's preferences, removes the temp
workspace (Chrome, puppeteer-core, the pnpm store), marks the ledger
finished and releases the machine lock. Each step is recorded as it completes,
so a `finish` that stops part-way can simply be run again.

`--discard` is for an invocation that stopped before any Round: it deletes the
Working theme too, and the branch when the branch holds no commits.

Without --discard it refuses while a Round is open: the Working theme it keeps
must hold kept Rounds only.
"""

import os
import shutil

from tuner import ledger, lock, repo, rounds, shopify, tools
from tuner.output import Refused, note, say

ORDER = 90


def register(sub):
    p = sub.add_parser("finish", help="delete the Control theme, remove Chrome, release the lock")
    p.add_argument("--discard", action="store_true",
                   help="also delete the Working theme, and the branch if it has no commits")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("finish")
    data = inv.data
    store = data["store"]["myshopify"]
    open_round = rounds.current(inv)
    if open_round is not None and not args.discard:
        raise Refused("round-open", "Round %d is open, so the Working theme may hold a change no "
                      "verdict kept" % open_round["n"],
                      "End it with `verdict`, or with `verdict --remove` when it cannot be "
                      "measured, then run `finish` again.")

    for role in ["control"] + (["working"] if args.discard else []):
        delete_theme(inv, store, role)
    working = data["themes"].get("working")
    if working and not working.get("deleted"):
        say("FINISH", "working-theme kept", "id=%s" % working["id"], 'name="%s"' % working["name"])

    return_to_start_branch(inv, discard=args.discard)

    if tools.restore_chrome_preferences(data["tools"].get("chrome_preferences")):
        inv.save()
        say("FINISH", "chrome-preferences restored")
    workspace = data.get("workspace")
    if workspace and os.path.isdir(workspace) and \
            os.path.basename(workspace).startswith("shopify-speed-tune-"):
        shutil.rmtree(workspace)
        say("FINISH", "workspace removed", "(Chrome, puppeteer-core, the pnpm store)")

    data["state"] = "finished"
    data["finished_at"] = ledger.now()
    inv.log("finish", "invocation finished")
    inv.save()
    lock.release(inv.id)
    say("FINISH", "lock released")
    say("FINISH", "done", "invocation=%s" % inv.id)
    return 0


def delete_theme(inv, store, role):
    theme = inv.data["themes"].get(role)
    if not theme or theme.get("deleted"):
        return
    found = shopify.theme(store, theme["id"])
    if found is None:
        theme["deleted"] = "already gone"
    elif found.get("role") != "unpublished":
        raise Refused("theme-not-unpublished",
                      "the %s theme %s is now %s; finish deletes only unpublished themes"
                      % (role, theme["id"], found.get("role")),
                      "Ask the developer what happened to it before going further.")
    else:
        shopify.delete(store, theme["id"])
        theme["deleted"] = ledger.now()
    inv.log("finish", "%s theme %s deleted" % (role, theme["id"]))
    inv.save()
    say("FINISH", "%s-theme deleted" % role, "id=%s" % theme["id"])


def return_to_start_branch(inv, discard):
    info = inv.data["repo"]
    root, branch, start = info["root"], info.get("branch"), info.get("start_branch")
    if not branch:
        return
    on_branch = repo.git(root, "branch", "--show-current").stdout.strip()
    if on_branch == branch:
        if repo.git(root, "status", "--porcelain", "--untracked-files=no").stdout.strip():
            note("%s has uncommitted changes, so the repo stays on %s" % (root, branch))
            return
        repo.git(root, "switch", "-q", start)
        on_branch = start
    commits = repo.git(root, "rev-list", "--count", "%s..%s" % (info["start_commit"], branch))
    if discard and commits.stdout.strip() == "0":
        repo.git(root, "branch", "-q", "-D", branch)
        say("FINISH", "branch deleted", branch, "(it held no commits)")
    else:
        say("FINISH", "branch kept", branch, "(repo on %s)" % on_branch)
