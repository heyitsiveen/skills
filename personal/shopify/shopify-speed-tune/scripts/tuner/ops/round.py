"""round: open a Round for one item of the approved plan, unless the Rounds are over.

A Round applies exactly one plan item. The program refuses a Round before the
plan is approved, a Round naming an item outside the approved plan, and a Round
naming an item an earlier Round already used, so the work stays bounded by
what the developer approved. With no --item it takes the first unused item, in
the plan's order.

Before opening, it runs the stop check `verdict` runs: when every page's kept
median already reaches its target, or no unused item is left, it prints the
TARGET lines and the STOP line and opens nothing.

The Round opens on the invocation's branch with no uncommitted change to a
tracked file, and records its base commit and the untracked files already
there: its change is then exactly what is edited until its verdict.
"""

from tuner import change, clock, ledger, planning, repo, rounds
from tuner.output import Refused, say

ORDER = 60


def register(sub):
    p = sub.add_parser("round", help="open a Round for one unused item of the approved plan")
    p.add_argument("--item", help="the plan item, by id (P1, P2, …); default: the first unused one")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("round")
    planning.require_approved(inv)
    item = planning.claim(inv, args.item) if args.item else None
    open_round = rounds.current(inv)
    if open_round is not None:
        raise Refused("round-open", "Round %d (%s) is still open" % (open_round["n"], open_round["item"]),
                      "End it with `verdict` first.")
    lines, reason = rounds.stop_check(inv)
    if reason:
        for tag, text in lines:
            say(tag, text)
        rounds.record_stop(inv, reason)
        return 0
    item = item or planning.claim(inv)
    root = inv.data["repo"]["root"]
    rounds.require_branch(inv)
    repo.require_clean(root)
    base = repo.head(root)
    entry = {"n": len(inv.data.get("rounds", [])) + 1, "item": item["id"], "state": "open",
             "opened_at": clock.now(), "base": base, "untracked": change.untracked(root)}
    inv.data.setdefault("rounds", []).append(entry)
    inv.log("round", "Round %d opened for %s at %s" % (entry["n"], item["id"], base[:12]))
    inv.save()
    say("ROUND", "%d opened item=%s pages=%s" % (entry["n"], item["id"], ",".join(item["pages"])))
    say("PLAN", planning.item_line(item))
    return 0
