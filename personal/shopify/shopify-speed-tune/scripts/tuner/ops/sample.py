"""sample: add Samples to one Measurement, by taking them or from report files.

Each Sample is taken as tuner.samples takes it. With no --count, it takes
Samples until the Measurement holds five, so a call that is cut off part-way is
finished by running it again. --report records existing Lighthouse report files
instead: the same checks, no Lighthouse run.
"""

import json

from tuner import ledger, samples, stats
from tuner.output import Failed, Refused, say

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
    url = inv.page_url(args.page)
    theme = inv.data["themes"].get(args.theme)
    if not theme or theme.get("deleted"):
        raise Refused("no-theme", "the invocation has no %s theme" % args.theme)
    if args.count is not None and args.count < 1:
        raise Refused("bad-count", "--count must be at least 1")
    have = len(samples.members(inv, args, url))
    room = stats.SAMPLES_PER_MEASUREMENT - have
    wanted = len(args.report) if args.report else (args.count or room)
    if wanted > room:
        raise Refused("measurement-complete",
                      "%s %s %s %s already holds %d of %d Samples"
                      % (args.label, args.page, args.device, args.theme, have,
                         stats.SAMPLES_PER_MEASUREMENT))

    if args.report:
        for path in args.report:
            with open(path, encoding="utf-8") as f:
                report = json.load(f)
            if samples.record(inv, args, url, theme, report, source="file") is None:
                return 1
    else:
        taken = samples.take(inv, args, url, theme, wanted)
        if taken < wanted:
            raise Failed("samples-rejected", "%d of %d Samples taken; see the rejections above"
                         % (taken, wanted), "Run the same command again to continue.")

    done = samples.members(inv, args, url)
    if len(done) == stats.SAMPLES_PER_MEASUREMENT:
        say("MEASUREMENT", stats.measurement_line(args.label, args.page, args.device, args.theme, done))
    return 0
