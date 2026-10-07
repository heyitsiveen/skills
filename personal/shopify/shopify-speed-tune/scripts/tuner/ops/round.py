"""round: open a Round for one item of the approved plan.

A Round applies exactly one plan item. The program refuses a Round before the
plan is approved, a Round naming an item outside the approved plan, and a Round
naming an item an earlier Round already used, so the work stays bounded by
what the developer approved.
"""

from tuner import ledger, planning
from tuner.output import say

ORDER = 60


def register(sub):
    p = sub.add_parser("round", help="open a Round for one unused item of the approved plan")
    p.add_argument("--item", required=True, help="the plan item, by id (P1, P2, …)")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("round")
    item = planning.claim(inv, args.item)
    rounds = inv.data.setdefault("rounds", [])
    n = len(rounds) + 1
    rounds.append({"n": n, "item": item["id"], "opened_at": ledger.now()})
    inv.log("round", "Round %d opened for %s" % (n, item["id"]))
    inv.save()
    say("ROUND", "%d opened item=%s pages=%s" % (n, item["id"], ",".join(item["pages"])))
    return 0
