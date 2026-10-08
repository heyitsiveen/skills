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

import json

from tuner import ledger, rounds, samples, stats
from tuner.output import Failed, Refused, say

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
    open_round = rounds.current(inv)
    if open_round is not None:
        raise Refused("round-open", "Round %d is open, so the Working theme may hold a change no "
                      "verdict kept" % open_round["n"],
                      "End it with `verdict`, or `verdict --remove`, first.")
    theme = inv.data["themes"].get("working")
    if not theme or theme.get("deleted"):
        raise Refused("no-theme", "the invocation has no working theme")
    if args.count is not None and args.count < 1:
        raise Refused("bad-count", "--count must be at least 1")
    target = stats.Measurement.of(inv, stats.FINAL, args.page, "desktop", "working")
    room = stats.SAMPLES_PER_MEASUREMENT - len(samples.members(inv, target))
    wanted = len(args.report) if args.report else (args.count or room)
    if wanted > room:
        raise Refused("measurement-complete", "the %s page's final desktop Measurement already "
                      "holds %d Samples" % (args.page, stats.SAMPLES_PER_MEASUREMENT))
    if args.report:
        for path in args.report:
            with open(path, encoding="utf-8") as f:
                report = json.load(f)
            if samples.record(inv, target, theme, report, source="file") is None:
                return 1
    else:
        taken = samples.take(inv, target, theme, wanted)
        if taken < wanted:
            raise Failed("samples-rejected", "%d of %d Samples taken; see the rejections above"
                         % (taken, wanted), "Run the same command again to continue.")
    done = samples.members(inv, target)
    if len(done) == stats.SAMPLES_PER_MEASUREMENT:
        say("MEASUREMENT", stats.measurement_line(target, done))
    return 0
