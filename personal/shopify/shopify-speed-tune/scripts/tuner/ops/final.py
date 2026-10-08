"""final: measure one page on desktop once more, at the end, on the Working theme.

Desktop decides nothing: it is measured in the baseline and again here, so the
report shows where it ended. The final Measurement is five desktop Samples of
the page on the Working theme, which holds every kept Round once the Rounds are
over. While a Round is open the Working theme may hold a change no verdict
kept, so it is refused then.

With no --count, it takes Samples until the Measurement holds five, so a call
cut off part-way is finished by running it again. --report records existing
Lighthouse report files instead: the same checks, no Lighthouse run.
"""

from tuner import ledger, rounds, samples, stats

ORDER = 70


def register(sub):
    p = sub.add_parser("final", help="measure one page on desktop on the Working theme, at the end")
    p.add_argument("--page", required=True, choices=stats.PAGE_ORDER)
    p.add_argument("--count", type=int,
                   help="Samples to take (default: as many as the Measurement still needs)")
    p.add_argument("--report", action="append", metavar="FILE",
                   help="record this Lighthouse report instead of taking a Sample (repeatable)")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("final")
    rounds.require_closed(inv, "final")
    target =stats.Measurement.of(inv, stats.FINAL, args.page, "desktop", "working")
    return samples.fill(inv, target, args.count, args.report)
