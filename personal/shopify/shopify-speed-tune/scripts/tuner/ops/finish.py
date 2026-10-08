"""finish: end the invocation, leaving only the Working theme and the branch.

Deletes the Control theme, puts the repo back on the branch the invocation
started from when that loses nothing (never with uncommitted changes, never
past a switch git refuses), stops any Chrome a job cut off part-way left
running, restores Chrome for Testing's preferences, removes the temp workspace
(Chrome, puppeteer-core and the smoke checker's project, the pnpm store), stops
the `caffeinate` that kept the Mac awake, marks the ledger finished and
releases the machine lock.

Then it reads back what it leaves, rather than trusting its own steps: the
theme library must list no Control theme and still the Working theme, the repo
must hold the branch, nothing may run from the workspace, which must be gone,
Chrome for Testing's preferences must hold what they held before the
invocation, and the lock must be free. Only then does it print `FINISH done`.
Anything left fails it with `cleanup-incomplete`, keeping the invocation open,
so `finish` can simply be run again once it is dealt with. Each step is
recorded as it completes, so a `finish` that stops part-way is finished by
running it again.

`--discard` is for an invocation no Round kept anything in, such as a `start`
that failed part-way: it deletes the Working theme too, and the branch when the
branch holds no commits. Once a Round was kept it refuses, since the Working
theme and the branch then hold work to publish.

It refuses while a Round is open, with or without --discard: the Working theme
it keeps must hold kept Rounds only, and a discard waits for the verdict.
"""

import os
import shutil

from tuner import awake, browser, clock, ledger, lock, repo, rounds, shopify, tools, write
from tuner.output import Failed, Refused, note, say

ORDER = 90


def register(sub):
    p = sub.add_parser("finish", help="delete the Control theme, remove Chrome, release the lock")
    p.add_argument("--discard", action="store_true",
                   help="also delete the Working theme, and the branch if it has no commits; "
                        "refused once a Round was kept")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("finish")
    data = inv.data
    store = inv.myshopify
    rounds.require_closed(inv, "finish")
    kept = [r["n"] for r in data.get("rounds", []) if r["state"] == "kept"]
    if args.discard and kept:
        raise Refused("kept-rounds", "%s kept %s, so the Working theme %s and the branch hold "
                      "work to publish" % (
                          "Round %d" % kept[0] if len(kept) == 1
                          else "Rounds %s" % ", ".join(str(n) for n in kept),
                          "its change" if len(kept) == 1 else "their changes",
                          data["themes"]["working"]["id"]),
                      "Run `finish` without --discard: it keeps the Working theme and the branch.")

    for role in ["control"] + (["working"] if args.discard else []):
        delete_theme(inv, role)
    working = data["themes"].get("working")
    if working and not working.get("deleted"):
        say("FINISH", "working-theme kept", "id=%s" % working["id"], 'name="%s"' % working["name"])

    return_to_start_branch(inv, discard=args.discard)

    stop_cut_off_chromes(inv)
    if tools.restore_chrome_preferences(data["tools"].get("chrome_preferences")):
        say("FINISH", "chrome-preferences restored")
    remove_workspace(inv)
    if awake.release(data.get("awake")):
        say("FINISH", "awake released")

    verify(inv, store, args.discard)
    data["state"] = "finished"
    data["finished_at"] = clock.now()
    inv.log("finish", "invocation finished")
    inv.save()
    lock.release(inv.id)
    if (lock.read() or {}).get("invocation") == inv.id:
        raise Failed("cleanup-incomplete", "the machine lock %s still names this invocation"
                     % lock.path(), "Run `finish` again.")
    say("FINISH", "lock released")
    if not (data.get("report") or {}).get("written_at"):
        note("no report was written: `report --invocation %s` writes it from the ledger" % inv.id)
    say("FINISH", "done", "invocation=%s" % inv.id)
    return 0


def delete_theme(inv, role):
    """Delete the invocation's `role` theme through the guarded write, which refuses one that
    is no longer unpublished or that another theme is named like."""
    theme = inv.data["themes"].get(role)
    if not theme or theme.get("deleted"):
        return
    theme["deleted"] = clock.now() if write.delete(inv, role) else "already gone"
    inv.log("finish", "%s theme %s deleted" % (role, theme["id"]))
    inv.save()
    say("FINISH", "%s-theme deleted" % role, "id=%s" % theme["id"])


def return_to_start_branch(inv, discard):
    """Put the repo back on the branch the invocation started from, when that loses nothing.

    Uncommitted changes keep it on the invocation's branch, and so does any switch
    git refuses, such as one that would overwrite an untracked file: the switch is
    never forced, so it never discards work, and what it did is read back.
    """
    info = inv.data["repo"]
    root, branch, start = info["root"], info.get("branch"), info.get("start_branch")
    if not branch:
        return
    on_branch = repo.git(root, "branch", "--show-current").stdout.strip()
    if on_branch == branch:
        if repo.git(root, "status", "--porcelain", "--untracked-files=no").stdout.strip():
            note("%s has uncommitted changes, so the repo stays on %s" % (root, branch))
            return
        switched = repo.git(root, "switch", "-q", start)
        if switched.returncode != 0:
            note("git did not switch the repo back to %s, so it stays on %s: %s"
                 % (start, branch, " ".join(switched.stderr.split())[:300]))
        on_branch = repo.git(root, "branch", "--show-current").stdout.strip()
    commits = repo.git(root, "rev-list", "--count", "%s..%s" % (info["start_commit"], branch))
    if discard and commits.stdout.strip() == "0" and on_branch != branch:
        if repo.git(root, "branch", "-q", "-D", branch).returncode == 0:
            say("FINISH", "branch deleted", branch, "(it held no commits)")
            return
    say("FINISH", "branch kept", branch, "(repo on %s)" % (on_branch or "a detached HEAD"))


def own_workspace(inv):
    """The invocation's temp workspace while it is still there, else None."""
    workspace = inv.data.get("workspace")
    if not workspace or not os.path.isdir(workspace) or \
            not os.path.basename(workspace).startswith("shopify-speed-tune-"):
        return None
    return workspace


def stop_cut_off_chromes(inv):
    """Stop each Chrome a job cut off part-way left running, before Chrome for Testing's
    preferences are put back, so none of them writes there again."""
    workspace = own_workspace(inv)
    if workspace is None:
        return
    chrome = (inv.data["tools"].get("chrome") or {}).get("path")
    for pid in browser.stop_leftovers(workspace, chrome):
        inv.log("finish", "stopped Chrome %d, left running by a job cut off part-way" % pid)
        inv.save()
        say("FINISH", "chrome stopped", "pid=%d" % pid, "(left by a job cut off part-way)")


def remove_workspace(inv):
    """Remove the workspace: never from under a process that still runs from it."""
    workspace = own_workspace(inv)
    if workspace is None:
        return
    still = browser.running_from(workspace)
    if still:
        raise Failed("cleanup-incomplete", "%d process%s still run%s from the invocation's "
                     "workspace %s" % (len(still), "" if len(still) == 1 else "es",
                                       "s" if len(still) == 1 else "", workspace),
                     *["pid %d: %s" % (pid, command[:200]) for pid, command in still],
                     "These were not started as this invocation's Chrome, so the program leaves "
                     "them alone: ask the developer to stop them, then run `finish` again.")
    shutil.rmtree(workspace)
    say("FINISH", "workspace removed", "(Chrome, puppeteer-core, the pnpm store)")


def verify(inv, store, discard):
    """Read back the theme library, the repo and the machine, printing a `FINISH verified`
    line for each that holds; refuse `done` while anything the invocation made is still
    there, other than the Working theme and the branch."""
    data = inv.data
    problems = []
    recorded = [(role, data["themes"][role]) for role in ("control", "working")
                if data["themes"].get(role)]
    library = {int(t["id"]): t for t in shopify.themes(store)} if recorded else {}
    themes = []
    for role, theme in recorded:
        found = library.get(int(theme["id"]))
        if role == "working" and not discard:
            if found is None:
                say("WARN", "working-theme-missing: the Working theme %s is no longer in the "
                            "theme library; whoever deleted it took every kept change on it"
                    % theme["id"])
            themes.append("working=%s" % (found.get("role") if found else "missing"))
        elif found is None:
            themes.append("%s=gone" % role)
        else:
            theme.pop("deleted", None)  # so the next `finish` deletes it again
            inv.save()
            problems.append("the %s theme %s is still in the theme library" % (role, theme["id"]))
    if themes and not problems:
        say("FINISH", "verified themes", *themes)

    info = data["repo"]
    if info.get("branch"):
        here = repo.git(info["root"], "branch", "--show-current").stdout.strip()
        kept = repo.branch_exists(info["root"], info["branch"])
        say("FINISH", "verified", "branch=%s" % (info["branch"] if kept else "deleted"),
            "repo-on=%s" % (here or "detached"))

    machine = []
    workspace = data.get("workspace")
    if workspace and os.path.exists(workspace):
        machine.append("the workspace %s is still there" % workspace)
    left = browser.running_from(workspace, wait=0) if workspace else []
    if left:
        machine.append("process %s still runs from the workspace"
                       % ", ".join(str(pid) for pid, _ in left))
    if awake.running(data.get("awake")):
        machine.append("the caffeinate %d that kept the Mac awake still runs"
                       % data["awake"]["pid"])
    preferences = data["tools"].get("chrome_preferences") or {}
    if preferences.get("saved") and not tools.chrome_preferences_as_before(preferences):
        machine.append("Chrome for Testing's preferences differ from before the invocation")
    if not machine:
        say("FINISH", "verified", "chrome=none", "workspace=gone",
            "awake=%s" % ("stopped" if data.get("awake") else "none"),
            "preferences=%s" % ("as-before" if preferences.get("saved") else "none"))
    problems += machine
    if problems:
        raise Failed("cleanup-incomplete", "; ".join(problems),
                     "Run `finish` again; when it stops here twice, show the developer this line.")
