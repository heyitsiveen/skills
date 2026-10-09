"""status: the invocation as the ledger holds it: every Measurement's median and range,
what the plan stop recorded, every smoke result, every Round, each page's kept
median against its target, and the stop once the Rounds stopped."""

from tuner import ledger, planning, rounds, smoke, stats
from tuner.output import say

ORDER = 80


def register(sub):
    p = sub.add_parser("status", help="print the invocation: every Measurement, Round and target "
                                      "so far")
    p.add_argument("--invocation", help="a finished invocation of this repo, by id")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.find(args.invocation)
    data = inv.data
    say("INVOCATION", inv.id, "state=%s" % data.get("state"), "store=%s" % inv.store_url,
        "requested_score=%s" % data.get("requested_score"),
        "hook=%s" % data["hook"]["status"] if data.get("hook") else "")
    for role in ("working", "control"):
        theme = data.get("themes", {}).get(role)
        if theme:
            say("THEME", role, "id=%s" % theme["id"], 'name="%s"' % theme.get("name"),
                "deleted" if theme.get("deleted") else "")
    for page, path in data.get("pages", {}).items():
        say("PAGE", page, inv.page_url(page))
    for measurement, samples in stats.measurements(data):
        say("MEASUREMENT", stats.measurement_line(measurement, samples))
    for tag, text in planning.status_lines(inv):
        say(tag, text)
    for record in data.get("smoke", []):
        say("SMOKE", smoke.result_line(record["label"], smoke.judge(record["pages"])))
    for rnd in data.get("rounds", []):
        say("ROUND", rounds.status_line(rnd))
        if rnd.get("verdict"):
            say("VERDICT", rounds.verdict_line(rnd))
    if (data.get("plan") or {}).get("approved_at"):
        for tag, text in rounds.stop_check(inv)[0]:
            if tag == "TARGET":
                say(tag, text)
    if data.get("stopped"):
        say("STOP", data["stopped"]["reason"])
    return 0
