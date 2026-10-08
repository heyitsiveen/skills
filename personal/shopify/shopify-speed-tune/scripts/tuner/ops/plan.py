"""plan: record the draft plan, show it, and approve it: the invocation's only stop.

`plan --items FILE` reads the draft from a JSON list of items, each stating its
`change`, its `pages`, the `cause` it addresses and its expected `effect`, plus
the `defects` it fixes when it fixes a known Golden theme defect. The program
checks every item, puts the known-defect items first (the rest keep the order
given), numbers them P1, P2, … and writes `plan.md` into the invocation's
folder for the developer. Recording again replaces the draft.

`plan --approve` makes the plan final. From then on a Round may use only an
item of this plan, and each item once. `plan` alone shows the plan again.
"""

from tuner import findings, ledger, planning, stats
from tuner.output import Refused, note, say
from tuner.text import COLUMNS, PAGE_NAMES, cell, psi_table, score, when

ORDER = 45


def register(sub):
    p = sub.add_parser("plan", help="record, show or approve the plan: the only stop")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--items", metavar="FILE", help="record the draft plan from a JSON list of items")
    mode.add_argument("--approve", action="store_true", help="approve the recorded plan; it is final")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("plan")
    if args.items:
        planning.record_plan(inv, planning.read_items(args.items))
    elif args.approve:
        planning.approve(inv)
    elif not inv.data.get("plan"):
        raise Refused("no-plan", "no plan is recorded", "Record it with `plan --items <file>`.")
    plan = inv.data["plan"]
    reports = {page: [r for _, r in findings.baseline(inv, page)] for page in stats.PAGE_ORDER}
    table = findings.costs(reports)

    for page in stats.PAGE_ORDER:
        say("PLAN", page_line(inv, page))
    for name, cells in table:
        say("COST", findings.cost_line(name, cells, stats.PAGE_ORDER))
    for item in plan["items"]:
        say("PLAN", planning.item_line(item))
    for entry in planning.unplanned_defects(inv):
        note("known defect %s was found but no item fixes it; plan it first, or say why not" % entry)
    if args.approve and not inv.data.get("psi"):
        note("no PageSpeed scores are recorded: record them with `psi` so the report can set them "
             "beside the baseline")
    path = inv.file("plan.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(inv, table))
    say("PLAN", "file", path)
    if plan.get("approved_at"):
        say("PLAN", "approved items=%d at %s" % (len(plan["items"]), plan["approved_at"]))
    else:
        say("PLAN", "draft items=%d" % len(plan["items"]))
    return 0


def _figures(values):
    median, low, high = values
    return "%d [%d-%d]" % (median, low, high)


def page_line(inv, page):
    return "page %s %s baseline=%s ceiling=%s target=%d" % (
        page, inv.page_url(page), _figures(planning.performance(inv, stats.BASELINE, page)),
        _figures(planning.ceiling(inv, page)), planning.target(inv, page))


def render(inv, table):
    data = inv.data
    plan = data["plan"]
    lines = [
        "# Speed plan: %s" % data["store"]["url"],
        "",
        "Invocation `%s`. Requested score %d. %s" % (
            inv.id, data["requested_score"],
            "Approved %s." % when(plan["approved_at"]) if plan.get("approved_at")
            else "Draft: not approved yet."),
        "",
        "## Pages",
        "",
        "| Page | URL | Baseline | Ceiling | Target |",
        "|---|---|---|---|---|",
    ]
    for page in stats.PAGE_ORDER:
        lines.append("| %s | %s | %s | %s | %d |" % (
            PAGE_NAMES[page], inv.page_url(page),
            score(planning.performance(inv, stats.BASELINE, page)),
            score(planning.ceiling(inv, page)), planning.target(inv, page)))
    lines += [
        "",
        "Mobile Performance scores, each the median of five Samples with their range. The "
        "**Baseline** is the Control theme as it is. The **Ceiling** is the same page with theme "
        "scripts, theme fonts and theme images other than the LCP image blocked, while stylesheets, "
        "apps and tags stay: an estimate of what theme work alone can reach. Each page's "
        "**target** is the lower of the requested score and its own Ceiling.",
        "",
    ]
    for page in stats.PAGE_ORDER:
        for text in (data.get("ceilings") or {}).get(page, {}).get("findings", []):
            lines.append("- %s: %s" % (PAGE_NAMES[page], text))
    if any((data.get("ceilings") or {}).get(p, {}).get("findings") for p in stats.PAGE_ORDER):
        lines.append("")
    lines += [
        "### Baseline in full (mobile)",
        "",
        "| Page | %s |" % " | ".join(COLUMNS),
        "|---|%s" % ("---|" * len(COLUMNS)),
    ]
    for page in stats.PAGE_ORDER:
        samples = stats.members(data["samples"], stats.Measurement.baseline(inv, page))
        figures = stats.summary(samples)
        lines.append("| %s | %s |" % (PAGE_NAMES[page],
                                      " | ".join(cell(m, *figures[m]) for m in stats.METRICS)))
    lines += ["", "## Apps and tags", ""] + findings.cost_table(table, stats.PAGE_ORDER)
    lines += ["", "## Plan", ""]
    for n, item in enumerate(plan["items"], 1):
        known = " *(known defect%s %s)*" % ("s" if len(item["defects"]) > 1 else "",
                                           ", ".join(item["defects"])) if item["defects"] else ""
        lines += [
            "%d. **%s**: %s%s" % (n, item["id"], item["change"], known),
            "   - Pages: %s" % ", ".join(item["pages"]),
            "   - Cause: %s" % item["cause"],
            "   - Expected effect: %s" % item["effect"],
        ]
    psi, warnings = planning.psi_lines(inv)
    if psi:
        lines += ["", "## PageSpeed comparison", ""] + psi_table(data["psi"], stats.PAGE_ORDER)
        lines += [""] + ["- %s" % w.split(": ", 1)[1] for w in warnings]
    if not plan.get("approved_at"):
        lines += ["", "## Before approving", "",
                  "Reply with your approval or the changes you want, and the PageSpeed mobile "
                  "score of each of the three pages, as you would screenshot them for the team."]
    return "\n".join(lines).rstrip() + "\n"
