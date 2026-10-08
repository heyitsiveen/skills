"""status: the invocation as the ledger holds it: every Measurement's median and range, and every smoke result."""

from tuner import ledger, smoke, stats
from tuner.output import say

ORDER = 80


def register(sub):
    p = sub.add_parser("status", help="print the invocation and every Measurement so far")
    p.add_argument("--invocation", help="a finished invocation of this repo, by id")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.find(args.invocation)
    data = inv.data
    say("INVOCATION", inv.id, "state=%s" % data.get("state"), "store=%s" % data["store"]["url"],
        "requested_score=%s" % data.get("requested_score"))
    for role in ("working", "control"):
        theme = data.get("themes", {}).get(role)
        if theme:
            say("THEME", role, "id=%s" % theme["id"], 'name="%s"' % theme.get("name"),
                "deleted" if theme.get("deleted") else "")
    for page, path in data.get("pages", {}).items():
        say("PAGE", page, inv.page_url(page))
    for key, samples in stats.measurements(data):
        say("MEASUREMENT", stats.measurement_line(*key, samples))
    for record in data.get("smoke", []):
        say("SMOKE", smoke.result_line(record["label"], smoke.judge(record["pages"])))
    return 0
