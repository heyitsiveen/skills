"""pairs: measure the open Round as five interleaved pairs on each of the three pages.

Each pair is one Control theme Sample, then one Working theme Sample, back to
back on mobile, so whatever the store and the network do at that moment meets
both themes. A pair is a win when the Working theme's Performance score is
higher, a loss when it is lower, and a tie when they are equal.

Pairs go round the pages: the first pair on home, collection and product, then
the second, and so on. A call starts no new pair once --minutes have passed
(default 6: a pair takes about two minutes, so a call fits a 10-minute window),
and the next call carries on.
A pair cut short is retaken whole, so its two Samples are always back to back.
--pair records a pair from two existing report files instead: the same checks,
no Lighthouse run.
"""

import argparse
import json
import time

from tuner import ledger, rounds, stats
from tuner.ops import sample
from tuner.output import Failed, Refused, say

ORDER = 64
MINUTES = 6


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


def target(rnd, page, role):
    return argparse.Namespace(label=rounds.label(rnd["n"]), page=page, device="mobile", theme=role)


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
        url = inv.page_url(page)
        label = rounds.label(rnd["n"])
        for role in ("control", "working"):
            members = stats.members(inv.data["samples"], label, page, url, "mobile", role)
            say("MEASUREMENT", stats.measurement_line(label, page, "mobile", role, members))


def discard(inv, recorded):
    recorded["discarded"] = "unpaired"
    inv.save()


def record_files(inv, rnd, page, files):
    url = inv.page_url(page)
    themes = inv.data["themes"]
    for control_file, working_file in files:
        k = next_pair(inv, rnd, page)
        recorded = {}
        for role, path in (("control", control_file), ("working", working_file)):
            with open(path, encoding="utf-8") as f:
                report = json.load(f)
            recorded[role] = sample.record(inv, target(rnd, page, role), url, themes[role], report,
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
        url = inv.page_url(page)
        recorded = {}
        for role in ("control", "working"):
            if (role, page) not in cookies:
                cookies[(role, page)] = sample.preview(inv, themes[role], url)
            recorded[role] = attempts(inv, rnd, page, role, url, cookies[(role, page)], k)
            if recorded[role] is None:
                if role == "working":
                    discard(inv, recorded["control"])
                raise Failed("samples-rejected", "pair %d on the %s page: no %s Sample could be "
                             "taken; see the rejections above" % (k, page, role),
                             "Run `pairs` again; the pair is retaken whole.")
        finish_pair(inv, rnd, page, k, recorded["control"], recorded["working"])


def attempts(inv, rnd, page, role, url, cookie, k):
    for _ in range(1 + sample.SPARE_ATTEMPTS):
        found = sample.attempt(inv, target(rnd, page, role), url, inv.data["themes"][role], cookie,
                               extra={"round": rnd["n"], "pair": k})
        if found is not None:
            return found
    return None
