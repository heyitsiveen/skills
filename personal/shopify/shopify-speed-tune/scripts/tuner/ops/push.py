"""push: send the open Round's change to the Working theme, through the guarded write.

The change is every theme file the working tree changes against the Round's
base commit. The program pushes exactly those paths, plus any an earlier push
of the Round sent, each by its own exact `--only`: a changed file is uploaded, a
deleted file is deleted from the theme, and nothing else on the theme is
touched. Before it writes, it reads the theme library back from the store: the
target must be the invocation's Working theme, still unpublished.

A change that is not theme code, touches the merchant's settings file, adds a
way to detect the test, or names a file the repo's .shopifyignore excludes is
refused, and nothing is written. A push whose JSON reports errors fails the
Round, which `verdict` then removes. The change may be pushed again until its
smoke check, which comes before the pairs; after that it is what the Round
measured.
"""

from tuner import change, ledger, rounds, write
from tuner.output import Failed, Refused, say

ORDER = 62


def register(sub):
    p = sub.add_parser("push", help="push the open Round's change to the Working theme")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("push")
    rnd = rounds.require_open(inv)
    if rnd.get("failed"):
        raise Refused("round-failed", "Round %d failed its push: %s" % (rnd["n"], rnd["failed"]),
                      "Run `verdict`: it removes the change and restores the Working theme.")
    if rounds.measured_yet(inv, rnd):
        raise Refused("round-measured", "Round %d was already measured as it was pushed"
                      % rnd["n"], "Its verdict decides it now: `pairs` once its smoke check "
                      "passed, then `verdict`.")
    rounds.require_place(inv, rnd)
    root = inv.data["repo"]["root"]
    entries = change.compute(root, rnd["base"], set(rnd["untracked"]))
    for status, path in entries:
        say("CHANGE", status, path, "template-json" if change.is_template_json(path) else "")
    if not entries:
        raise Refused("no-change", "Round %d changes no file yet" % rnd["n"],
                      "Make the plan item's change first.")
    change.check(root, rnd["base"], entries)
    paths = sorted({p for _, p in entries} | set(rnd.get("pushed_paths", [])))
    theme = write.guard(inv, "working", paths)

    # Recorded before the CLI runs: a push cut off part-way may have written some
    # files, and removing the Round pushes every one of these paths back.
    rnd["pushed_paths"] = paths
    attempt = {"theme": "working", "id": theme["id"], "paths": paths, "at": ledger.now(),
               "result": "sent"}
    rnd.setdefault("pushes", []).append(attempt)
    rnd.pop("change", None)
    inv.save()
    pushed = write.send(inv, theme, paths)

    if pushed.warning:
        attempt.update(result="errors", warning=pushed.warning, errors=pushed.errors)
        rnd["failed"] = "push-errors"
        inv.log("push", "Round %d failed: the Working theme %s refused the change: %s"
                % (rnd["n"], theme["id"], pushed.errors or pushed.warning))
        inv.save()
        notes = ["%s: %s" % (path, message) for path, messages in sorted(pushed.errors.items())
                 for message in messages] or [pushed.warning]
        raise Failed("push-errors", "the Working theme %s refused the change, so Round %d failed"
                     % (theme["id"], rnd["n"]), *notes,
                     "Run `verdict`: it removes the change and restores the Working theme.")
    if not pushed.ok:
        attempt.update(result="failed", detail=pushed.failure)
        inv.log("push", "Round %d push to the Working theme %s did not finish: %s"
                % (rnd["n"], theme["id"], pushed.failure))
        inv.save()
        raise Failed("push-failed", "the push to the Working theme %s did not finish: %s"
                     % (theme["id"], pushed.failure),
                     "Run `push` again; when it fails twice, stop and show the developer.")
    attempt["result"] = "ok"
    rnd["change"] = {"entries": [list(e) for e in entries],
                     "fingerprint": change.fingerprint(root, entries),
                     "hashes": change.hashes(root, paths),
                     "template_json": [p for _, p in entries if change.is_template_json(p)]}
    inv.log("push", "Round %d pushed %d paths to the Working theme %s"
            % (rnd["n"], len(paths), theme["id"]))
    inv.save()
    say("PUSH", "working theme=%s paths=%d ok" % (theme["id"], len(paths)))
    return 0
