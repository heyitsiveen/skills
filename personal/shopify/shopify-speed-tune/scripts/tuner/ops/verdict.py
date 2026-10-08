"""verdict: decide the open Round, carry the decision out, and check whether the Rounds stop.

The program decides; nothing here rests on reading a transcript:

- keep only when the change wins at least 4 of 5 pairs on one of its target
  pages, no page loses 4 or more, no page's median accessibility score drops,
  and the smoke check finds nothing the Working theme does worse
- remove a Round whose push failed, without measuring it

Keep: one Conventional Commit of exactly the Round's change on the invocation's
branch, running the repo's own commit hooks unless the developer approved
--no-verify at `start` (a change the hooks refuse is removed instead), then the
same state pushed to the Control theme. Remove: the working tree back at the
last commit and the Working theme pushed back to it. Each step is recorded as
it completes, so a verdict cut off part-way is finished by running it again.

--remove ends a Round the program cannot judge: one never pushed, or one whose
pairs or smoke check cannot be taken. A measured, checked Round is decided by
the rule alone.
"""

from tuner import change, hook, ledger, rounds, smoke, stats, write
from tuner.output import Failed, Refused, note, say

ORDER = 66


def register(sub):
    p = sub.add_parser("verdict", help="keep or remove the open Round's change, then check the stop")
    p.add_argument("--remove", action="store_true",
                   help="end a Round that cannot be pushed, measured or smoke-checked by removing "
                        "its change")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("verdict")
    rnd = rounds.require_open(inv)
    if not rnd.get("verdict"):
        rnd["verdict"] = judge(inv, rnd, args.remove)
        if rnd["verdict"]["decision"] == "keep":
            commit(inv, rnd)
        rnd["verdict"]["at"] = ledger.now()
        inv.log("verdict", "Round %d: %s" % (rnd["n"], rounds.verdict_line(rnd)))
        inv.save()
    show(inv, rnd)
    if rnd["verdict"]["decision"] == "keep":
        keep(inv, rnd)
    else:
        remove(inv, rnd)
    lines, reason = rounds.stop_check(inv)
    for tag, text in lines:
        say(tag, text)
    if reason:
        rounds.record_stop(inv, reason)
    return 0


def judge(inv, rnd, forced):
    if rnd.get("failed"):
        return rounds.removal("push-errors")
    if not rnd.get("change"):
        if forced:
            return rounds.removal("not-pushed")
        raise Refused("round-not-pushed", "Round %d's change never reached the Working theme"
                      % rnd["n"], "Push it with `push`. When the plan item cannot be made, "
                      "`verdict --remove` ends the Round.")
    rounds.require_place(inv, rnd)
    root = inv.data["repo"]["root"]
    entries = change.compute(root, rnd["base"], set(rnd["untracked"]))
    if change.fingerprint(root, entries) != rnd["change"]["fingerprint"]:
        # What was measured is not what the tree holds, so the tree cannot be kept.
        return rounds.removal("changed-since-push")
    if not rounds.complete(inv, rnd):
        if forced:
            return rounds.removal("unmeasured")
        raise Refused("round-unmeasured", "Round %d does not hold five pairs on every page yet"
                      % rnd["n"], "Run `pairs` until it prints `PAIRS %d complete`. When pairs "
                      "cannot be taken, `verdict --remove` ends the Round." % rnd["n"])
    if rounds.smoke_record(inv, rnd) is None:
        if forced:
            return rounds.removal("unchecked")
        raise Refused("round-unchecked", "Round %d has no smoke check yet" % rnd["n"],
                      "Run `smoke`. When it cannot run, `verdict --remove` ends the Round.")
    if forced:
        raise Refused("round-measured", "Round %d is measured and smoke-checked, so the rule "
                      "decides it" % rnd["n"], "Run `verdict` without --remove.")
    return rounds.decide(inv, rnd)


def commit(inv, rnd):
    """Commit the kept change once; a commit the repo's hooks refuse turns it into a removal.
    The hooks run unless the developer approved --no-verify for this invocation at start."""
    root = inv.data["repo"]["root"]
    paths = [p for _, p in rnd["change"]["entries"]]
    subject, body = rounds.commit_message(inv, rnd)
    done = change.commit(root, rnd["base"], paths, subject, body, verify=hook.verifies(inv.data))
    if done.sha is None:
        rnd["verdict"].update(decision="remove", reasons=["commit-refused"])
        rnd["commit_refused"] = done.output
        return
    rnd["commit"] = done.sha
    now = change.hashes(root, paths)
    rnd["reformatted"] = [p for p in paths if now[p] != rnd["change"]["hashes"].get(p)]


def show(inv, rnd):
    if rnd["verdict"].get("pages"):
        for page in stats.PAGE_ORDER:
            say("PAIRS", rounds.summary_line(rnd, page, rnd["verdict"]["pages"][page]))
        record = rounds.smoke_record(inv, rnd)
        say("SMOKE", smoke.result_line(record["label"], smoke.judge(record["pages"])))
    say("VERDICT", rounds.verdict_line(rnd))
    for line in rnd.get("commit_refused") or []:
        note(line)


def push(inv, rnd, role, paths, step):
    """Push `paths` to the invocation's `role` theme for the verdict, once."""
    if rnd.get(step):
        return
    _, theme, pushed = write.push(inv, role, paths)
    if not pushed.ok:
        detail = ["%s: %s" % (p, m) for p, ms in sorted(pushed.errors.items()) for m in ms]
        raise Failed("push-errors" if pushed.warning else "push-failed",
                     "the push to the %s theme %s for Round %d's verdict did not succeed: %s"
                     % (role, theme["id"], rnd["n"], pushed.warning or pushed.failure), *detail,
                     "Run `verdict` again to retry it; when it fails twice, stop and show the "
                     "developer.")
    rnd[step] = ledger.now()
    inv.log("verdict", "Round %d: pushed %d paths to the %s theme %s"
            % (rnd["n"], len(paths), role, theme["id"]))
    inv.save()
    say("PUSH", "%s theme=%s paths=%d ok" % (role, theme["id"], len(paths)))


def keep(inv, rnd):
    if rnd.get("reformatted"):
        note("the commit hook rewrote %s; both themes get the committed version"
             % ", ".join(rnd["reformatted"]))
        push(inv, rnd, "working", rnd["reformatted"], "working_synced")
    push(inv, rnd, "control", rnd["pushed_paths"], "control_pushed")
    close(inv, rnd, "kept")
    say("ROUND", "%d kept commit=%s" % (rnd["n"], rnd["commit"][:12]))


def remove(inv, rnd):
    root = inv.data["repo"]["root"]
    if not rnd.get("restored"):
        entries = change.compute(root, rnd["base"], set(rnd["untracked"]))
        paths = sorted({p for _, p in entries} | set(rnd.get("pushed_paths", [])))
        change.restore(root, rnd["base"], paths)
        rnd["restored"] = ledger.now()
        inv.log("verdict", "Round %d: working tree restored for %s" % (rnd["n"], ", ".join(paths)))
        inv.save()
    if rnd.get("pushes"):
        push(inv, rnd, "working", rnd["pushed_paths"], "working_restored")
    close(inv, rnd, "removed")
    say("ROUND", "%d removed" % rnd["n"])


def close(inv, rnd, state):
    rnd["state"] = state
    rnd["closed_at"] = ledger.now()
    inv.log("verdict", "Round %d %s" % (rnd["n"], state))
    inv.save()
