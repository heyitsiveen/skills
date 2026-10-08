"""sample: add Samples to one Measurement, by taking them or from report files.

Each Sample is taken as tuner.samples takes it. With no --count, it takes
Samples until the Measurement holds five, so a call that is cut off part-way is
finished by running it again. --report records existing Lighthouse report files
instead: the same checks, no Lighthouse run.
"""

from tuner import ledger, samples, stats

ORDER = 30
PAGES = ("home", "collection", "product")
DEVICES = ("mobile", "desktop")
THEMES = ("control", "working")


def register(sub):
    p = sub.add_parser("sample", help="take Samples of one page, or record them from report files")
    p.add_argument("--page", required=True, choices=PAGES)
    p.add_argument("--device", required=True, choices=DEVICES)
    p.add_argument("--theme", default="control", choices=THEMES,
                   help="the theme to measure (default control)")
    p.add_argument("--label", default="baseline",
                   help="the Measurement the Samples belong to (default baseline)")
    p.add_argument("--count", type=int,
                   help="Samples to take (default: as many as the Measurement still needs)")
    p.add_argument("--report", action="append", metavar="FILE",
                   help="record this Lighthouse report instead of taking a Sample (repeatable)")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("sample")
    measurement = stats.Measurement.of(inv, args.label, args.page, args.device, args.theme)
    return samples.fill(inv, measurement, args.count, args.report)
