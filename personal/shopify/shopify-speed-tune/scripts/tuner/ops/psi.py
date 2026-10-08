"""psi: compare the developer's three PageSpeed mobile scores with the baseline.

The developer types the scores they would screenshot for the team at the plan
stop. Each is set beside the matching page's baseline mobile median; a gap of
more than 10 points, the upper end of the run-to-run variance Shopify
documents, prints a WARN line, so the developer knows before the Rounds whether
the final PageSpeed screenshot can match the report. Running it again replaces
the scores.
"""

from tuner import ledger, planning, stats
from tuner.output import say

ORDER = 50


def register(sub):
    p = sub.add_parser("psi", help="set the developer's PageSpeed mobile scores beside the baseline")
    for page in stats.PAGE_ORDER:
        p.add_argument("--" + page, type=int, required=True,
                       help="PageSpeed mobile score of the %s page" % page)
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("psi")
    planning.record_psi(inv, {page: getattr(args, page) for page in stats.PAGE_ORDER})
    lines, warnings = planning.psi_lines(inv)
    for line in lines:
        say("PSI", line)
    for warning in warnings:
        say("WARN", warning)
    return 0
