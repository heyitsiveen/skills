"""diagnose: what the baseline already says about each page, and the store's known defects.

It reads the three pages' baseline mobile Samples, which are already in the
invocation's folder, so it takes no Sample. It prints:

- FINDING: per page, the Lighthouse reports' own findings: the LCP element and
  its breakdown, the render-blocking requests, the layout shifts and the long
  tasks, each request named by its owner (theme, the page's HTML, Shopify, an
  app, or a third-party host).
- DEFECT: each known Golden theme defect (references/known-defects.md), found
  by its detection rule or clear; a theme not built on Golden gets `none`.
- COST: the cost of every app and tag, from Lighthouse's third-party summary.

The defect check is kept in the ledger, where `plan` reads it.
"""

from tuner import clock, defects, findings, ledger, stats
from tuner.output import say

ORDER = 40


def register(sub):
    p = sub.add_parser("diagnose", help="read the baseline Samples: app and tag costs, findings, "
                                        "known defects")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("diagnose")
    reports = {page: [r for _, r in findings.baseline(inv, page)] for page in stats.PAGE_ORDER}
    checked = defects.check(inv.root, reports)
    inv.data["defects"] = dict(checked, checked_at=clock.now())
    inv.log("diagnose", "known defects: %s" % (", ".join(
        r["id"] for r in checked["results"] if r["state"] == "found") or "none"))
    inv.save()
    for page in stats.PAGE_ORDER:
        owners = findings.Owners(inv.store_url,
                                 inv.data["themes"]["control"]["asset_path"], inv.page_url(page))
        for line in (findings.lcp_line(reports[page]),
                     findings.render_blocking_line(reports[page], owners),
                     findings.layout_shift_line(reports[page]),
                     findings.long_tasks_line(reports[page], owners)):
            say("FINDING", page, line)
    for line in defects.lines(checked):
        say("DEFECT", line)
    for name, cells in findings.costs(reports):
        say("COST", findings.cost_line(name, cells, stats.PAGE_ORDER))
    return 0
