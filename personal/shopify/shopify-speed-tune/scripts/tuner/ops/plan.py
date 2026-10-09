"""plan: record the draft plan, show it, and approve it: the invocation's only stop.

`plan --items FILE` reads the draft from a JSON list of items, each stating its
`change`, its `pages`, the `cause` it addresses and its expected `effect`, plus
the `defects` it fixes when it fixes a known Golden theme defect. The program
checks every item, puts the known-defect items first (the rest keep the order
given), numbers them P1, P2, … and writes `plan.md` into the invocation's
folder for the developer. Recording again replaces the draft.

Each Round measures its item alone on top of the Rounds kept before it, and any
earlier item may be removed, so an item fixing D2 must fix D1 too while
`diagnose` finds D1: an eager image needs D1's fix.

The plan carries the baseline smoke check's SMOKE lines, judged from its stored
results by the rule in force: a Round whose check fails is removed unmeasured,
so the developer approves knowing whether the check holds on this store.

`plan --approve` makes the plan final. From then on a Round may use only an
item of this plan, and each item once. `plan` alone shows the plan again.
"""

from tuner import findings, ledger, planning, smoke, stats
from tuner.output import Refused, note, say
from tuner.text import COLUMNS, cell, page_name, psi_table, score, when

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
    checked = baseline_smoke(inv)
    for line in checked[1] if checked else []:
        say("SMOKE", line)
    for name, cells in table:
        say("COST", findings.cost_line(name, cells, stats.PAGE_ORDER))
    for item in plan["items"]:
        say("PLAN", planning.item_line(item))
    for entry in planning.unplanned_defects(inv):
        note("known defect %s was found but no item fixes it; plan it first, or say why not" % entry)
    if args.approve and not inv.data.get("psi"):
        note("the developer's PageSpeed Insights mobile Performance scores are not recorded: "
             "record them with `psi` so the report can set them beside the baseline")
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


def baseline_smoke(inv):
    """(passed, [SMOKE line text]) for the baseline smoke check, judged from its stored results
    by the rule in force: a line per finding, then its result line. None while it has none."""
    record = smoke.recorded(inv.data, stats.BASELINE)
    if record is None:
        return None
    judgement = smoke.judge(record["pages"])
    return judgement.passed, judgement.lines(record["label"]) + [
        smoke.result_line(record["label"], judgement)]


def smoke_section(inv):
    checked = baseline_smoke(inv)
    if checked is None:
        return ["No baseline smoke result is recorded: the smoke check did not reach a result "
                "before this plan."]
    passed, lines = checked
    if passed:
        return ["Before any change, the smoke check loaded each page on both themes as a phone "
                "and found the Working theme doing everything the Control theme does: "
                "`SMOKE %s`." % lines[-1]]
    return ["Before any change, the smoke check loaded each page on both themes as a phone. Both "
            "are still copies of the published theme, yet it found the Working theme doing "
            "worse, so the check is unsteady on this store, and a Round it fails the same way is "
            "removed without being measured:", ""] + ["- `SMOKE %s`" % line for line in lines]


def render(inv, table):
    data = inv.data
    plan = data["plan"]
    lines = [
        "# Speed plan: %s" % inv.store_url,
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
            page_name(page), inv.page_url(page),
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
            lines.append("- %s: %s" % (page_name(page), text))
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
        lines.append("| %s | %s |" % (page_name(page),
                                      " | ".join(cell(m, *figures[m]) for m in stats.METRICS)))
    lines += ["", "### Smoke check", ""] + smoke_section(inv)
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
                  "Reply with your approval or the changes you want, and the mobile Performance "
                  "score PageSpeed Insights gives each of the three pages, as you would "
                  "screenshot it for the team."]
    return "\n".join(lines).rstrip() + "\n"
