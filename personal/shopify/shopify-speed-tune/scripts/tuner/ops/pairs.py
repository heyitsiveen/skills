"""pairs: measure the open Round as five interleaved pairs on each of the three pages.

Pairs follow the Round's smoke check, and only a passing one: the check warms
the store's cache with the changed files, and a change it finds broken is
removed by `verdict` without pairs.

Each pair is one Control theme Sample, then one Working theme Sample, back to
back on mobile, so whatever the store and the network do at that moment meets
both themes. A pair is a win when the Working theme's Performance score is
higher, a loss when it is lower, and a tie when they are equal.

Pairs go round the pages: the first pair on home, collection and product, then
the second, and so on. A call starts no new pair once --minutes have passed
(default 6: a pair takes about two minutes, so a call fits a 10-minute window),
and the next call carries on.

A pair's two Samples are always back to back. Both themes' preview cookies are
had before its first Sample, so a pause the store's HTTP 429 forces comes
before the pair, never inside it. A pair cut short, or whose Working Sample is
rejected, is retaken whole; the Control Sample it leaves is set aside, kept in
the ledger as unpaired but counted nowhere.
--pair records a pair from two existing report files instead: the same checks,
without running Lighthouse.
"""

import json
import time

from tuner import ledger, rounds, samples, stats
from tuner.output import Failed, Refused, note, say

ORDER = 64
MINUTES = 6
ROLES = ("control", "working")


def register(sub):
    p = sub.add_parser("pairs", help="take the open Round's interleaved pairs on the three pages")
    p.add_argument("--page", choices=stats.PAGE_ORDER, help="take pairs on this page only")
    p.add_argument("--minutes", type=float, default=MINUTES,
                   help="start no new pair after this many minutes (default %d)" % MINUTES)
    p.add_argument("--pair", nargs=2, action="append", metavar=("CONTROL", "WORKING"),
                   help="record a pair from two Lighthouse report files instead (repeatable; "
                        "needs --page)")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("pairs")
    rnd = rounds.require_open(inv)
    rounds.require_measurable(inv, rnd)
    rounds.require_smoke_passed(inv, rnd)
    pages = [args.page] if args.page else list(stats.PAGE_ORDER)
    for page in pages:
        rounds.discard_unpaired(inv, rnd, page)
    inv.save()
    if args.pair:
        if not args.page:
            raise Refused("bad-usage", "--pair needs --page: the page its reports are of")
        record_files(inv, rnd, args.page, args.pair)
    else:
        take(inv, rnd, pages, args.minutes * 60)
    left = {page: len(rounds.pairs(inv, rnd, page)) for page in stats.PAGE_ORDER}
    if all(n == rounds.PAIRS_PER_PAGE for n in left.values()):
        say("PAIRS", "%d complete" % rnd["n"])
    else:
        say("PAIRS", "%d incomplete %s" % (rnd["n"], " ".join(
            "%s=%d/%d" % (page, left[page], rounds.PAIRS_PER_PAGE) for page in stats.PAGE_ORDER)))
    return 0


def target(inv, rnd, page, role):
    """The Round's Measurement of `page` on the `role` theme: mobile, as every pair is."""
    return stats.Measurement.of(inv, rounds.label(rnd["n"]), page, "mobile", role)


def next_pair(inv, rnd, page):
    done = len(rounds.pairs(inv, rnd, page))
    if done >= rounds.PAIRS_PER_PAGE:
        raise Refused("pairs-complete", "the %s page already holds %d pairs"
                      % (page, rounds.PAIRS_PER_PAGE))
    return done + 1


def finish_pair(inv, rnd, page, k, control, working):
    say("PAIR", rounds.pair_line(rnd, page, k, control, working))
    if len(rounds.pairs(inv, rnd, page)) == rounds.PAIRS_PER_PAGE:
        say("PAIRS", rounds.summary_line(rnd, page, rounds.page_summary(inv, rnd, page)))
        for role in ("control", "working"):
            measurement = target(inv, rnd, page, role)
            say("MEASUREMENT", stats.measurement_line(measurement,
                                                      samples.members(inv, measurement)))


def discard(inv, recorded):
    recorded["discarded"] = "unpaired"
    inv.save()


def record_files(inv, rnd, page, files):
    themes = inv.data["themes"]
    for control_file, working_file in files:
        k = next_pair(inv, rnd, page)
        recorded = {}
        for role, path in (("control", control_file), ("working", working_file)):
            with open(path, encoding="utf-8") as f:
                report = json.load(f)
            recorded[role] = samples.record(inv, target(inv, rnd, page, role), themes[role], report,
                                            source="file", extra={"round": rnd["n"], "pair": k})
            if recorded[role] is None:
                if role == "working":
                    discard(inv, recorded["control"])
                raise Failed("samples-rejected", "pair %d on the %s page was not recorded" % (k, page))
        finish_pair(inv, rnd, page, k, recorded["control"], recorded["working"])


def take(inv, rnd, pages, budget):
    """Take pairs round the pages until each holds five or the time budget is spent."""
    queue = sorted(((k, stats.PAGE_ORDER.index(page), page) for page in pages
                    for k in range(len(rounds.pairs(inv, rnd, page)) + 1,
                                   rounds.PAIRS_PER_PAGE + 1)))
    themes = inv.data["themes"]
    cookies = {}
    began = time.monotonic()
    for taken, (k, _, page) in enumerate(queue):
        if taken and time.monotonic() - began >= budget:
            return
        # Both cookies before the pair's first Sample: a pause the store's HTTP 429 forces
        # then comes before the pair, never between its two Samples.
        for role in ROLES:
            if (role, page) not in cookies:
                cookies[(role, page)] = samples.preview(inv, themes[role], inv.page_url(page))
        control, working = take_pair(inv, rnd, page, k,
                                     {role: cookies[(role, page)] for role in ROLES})
        finish_pair(inv, rnd, page, k, control, working)


def take_pair(inv, rnd, page, k, cookies):
    """(Control Sample, Working Sample), taken back to back. A rejected Working Sample
    would leave a whole Sample's time after its Control Sample, so that Control Sample is
    set aside and the pair taken again whole, within the spare attempts."""
    for _ in range(1 + samples.SPARE_ATTEMPTS):
        recorded = {}
        for role in ROLES:
            recorded[role] = samples.attempt(inv, target(inv, rnd, page, role),
                                             inv.data["themes"][role], cookies[role],
                                             extra={"round": rnd["n"], "pair": k})
            if recorded[role] is None:
                break
        else:
            return recorded["control"], recorded["working"]
        if recorded["control"] is not None:
            discard(inv, recorded["control"])
            note("pair %d on the %s page is retaken whole: its Working Sample was rejected, so "
                 "its Control Sample %s is set aside" % (k, page, recorded["control"]["id"]))
    raise Failed("samples-rejected", "pair %d on the %s page: no %s Sample could be taken; see "
                 "the rejections above" % (k, page, role),
                 "Run `pairs` again; the pair is retaken whole.")
