"""sample: add Samples to a page's baseline Measurement, by taking them or from report files.

The baseline is each page on the Control theme, mobile and desktop, before any
Round. Each Sample is taken as tuner.samples takes it. With no --count, it
takes Samples until the Measurement holds five, so a call that is cut off
part-way is finished by running it again. --report records existing
Lighthouse report files instead: the same checks, no Lighthouse run.
"""

from tuner import ledger, samples, stats

ORDER = 30


def register(sub):
    p = sub.add_parser("sample", help="take a page's baseline Samples, or record them from "
                                      "report files")
    p.add_argument("--page", required=True, choices=stats.PAGE_ORDER)
    p.add_argument("--device", required=True, choices=stats.DEVICES)
    p.add_argument("--count", type=int,
                   help="Samples to take (default: as many as the Measurement still needs)")
    p.add_argument("--report", action="append", metavar="FILE",
                   help="record this Lighthouse report instead of taking a Sample (repeatable)")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("sample")
    measurement = stats.Measurement.baseline(inv, args.page, args.device)
    return samples.fill(inv, measurement, args.count, args.report)
