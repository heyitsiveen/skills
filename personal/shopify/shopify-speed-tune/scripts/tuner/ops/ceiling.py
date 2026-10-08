"""ceiling: measure one page's Ceiling on the Control theme, mobile.

The Ceiling is the most theme work can reach with the store's apps and tags
left as they are. It is measured as five mobile Samples with every theme-owned
request blocked that the first screen does not need: theme scripts, theme
fonts, and theme images other than the page's LCP image. Stylesheets stay,
because removing them changes what the first screen is; apps and tags stay.
The page's target is the lower of the requested score and that Ceiling.

The blocked patterns are built once from the page's five baseline mobile
Samples and kept in the ledger, so every Ceiling Sample blocks the same thing.
Lighthouse has no allow-list, so no pattern that matches the LCP image is ever
emitted. --report records existing Lighthouse report files instead.
"""

import argparse
import json

from tuner import findings, ledger, planning, probe, samples, stats
from tuner.output import Failed, Refused, note, say

ORDER = 35
LABEL = "ceiling"


def register(sub):
    p = sub.add_parser("ceiling", help="measure one page's Ceiling: mobile, theme requests blocked")
    p.add_argument("--page", required=True, choices=stats.PAGE_ORDER)
    p.add_argument("--count", type=int,
                   help="Samples to take (default: as many as the Measurement still needs)")
    p.add_argument("--report", action="append", metavar="FILE",
                   help="record this Lighthouse report instead of taking a Sample (repeatable)")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("ceiling")
    url = inv.page_url(args.page)
    theme = inv.data["themes"].get("control")
    if not theme or theme.get("deleted"):
        raise Refused("no-theme", "the invocation has no control theme")
    if args.count is not None and args.count < 1:
        raise Refused("bad-count", "--count must be at least 1")
    found = probe_for(inv, args.page, url)
    for pattern in found["patterns"]:
        say("CEILING", args.page, "block", pattern)
    for place in found["protect"]:
        say("CEILING", args.page, "protect", place)
    for text in found["notes"]:
        note("%s: %s" % (args.page, text))

    target = argparse.Namespace(label=LABEL, page=args.page, device="mobile", theme="control")
    have = len(samples.members(inv, target, url))
    room = stats.SAMPLES_PER_MEASUREMENT - have
    wanted = len(args.report) if args.report else (args.count or room)
    if wanted > room:
        raise Refused("measurement-complete", "the %s page's Ceiling already holds %d of %d "
                      "Samples" % (args.page, have, stats.SAMPLES_PER_MEASUREMENT))
    if args.report:
        for path in args.report:
            with open(path, encoding="utf-8") as f:
                report = json.load(f)
            if samples.record(inv, target, url, theme, report, source="file", probe=found) is None:
                return 1
    else:
        taken = samples.take(inv, target, url, theme, wanted, probe=found)
        if taken < wanted:
            raise Failed("samples-rejected", "%d of %d Samples taken; see the rejections above"
                         % (taken, wanted), "Run the same command again to continue.")

    done = samples.members(inv, target, url)
    if len(done) == stats.SAMPLES_PER_MEASUREMENT:
        say("MEASUREMENT", stats.measurement_line(LABEL, args.page, "mobile", "control", done))
        found["findings"] = read_ceiling(inv, args.page, url, done)
        inv.save()
        for text in found["findings"]:
            note("%s: %s" % (args.page, text))
        say("CEILING", planning.ceiling_line(inv, args.page))
    return 0


def _painted(found):
    """What a largest paint was: an image by where it came from, text by its element."""
    if found["kind"] == "image" and found["url"]:
        return ("image", probe.place(found["url"]))
    return (found["kind"], found["selector"])


def _reports(inv, samples):
    out = []
    for s in samples:
        with open(inv.file(s["report"]), encoding="utf-8") as f:
            out.append(json.load(f))
    return out


def read_ceiling(inv, page, url, samples):
    """What the developer should know before trusting this page's Ceiling."""
    baseline = stats.members(inv.data["samples"], stats.BASELINE, page, url, "mobile", "control")
    before = _reports(inv, baseline)
    painted = {_painted(probe.lcp(r)) for r in before}
    moved = [probe.lcp(r) for r in _reports(inv, samples)]
    moved = [m for m in moved if _painted(m) not in painted]
    out = []
    if moved:
        common = findings.most_common([m["selector"] for m in moved])
        element = " > ".join((common or "?").split(" > ")[-2:])
        kind = next(m["kind"] for m in moved if m["selector"] == common)
        if kind != "text":
            what = "an image"
        elif element.split(" > ")[-1].startswith("img"):
            what = "the alt text of an image that never loaded"
        else:
            what = "text"
        where = "%s (%s)" % (element, what)
        if sum(1 for r in before if probe.lazy_lcp(r)) >= len(before) / 2.0:
            out.append("the LCP image loads only through a theme script (a lazy loader), so with "
                       "theme scripts blocked it never loaded, and the largest paint moved to %s "
                       "in %d of %d Ceiling Samples. This Ceiling leaves out that image's own "
                       "loading: read it as a rough estimate" % (where, len(moved), len(samples)))
        else:
            out.append("the largest paint moved off the baseline's LCP element to %s in %d of %d "
                       "Ceiling Samples, so this Ceiling measures a different first screen: read "
                       "it as a rough estimate" % (where, len(moved), len(samples)))
    ceiling_median = planning.ceiling(inv, page)[0]
    baseline_median = planning.baseline_median(inv, page)
    if ceiling_median <= baseline_median:
        out.append("the Ceiling (%d) is not above the baseline median (%d): blocking the theme's "
                   "optional requests did not raise the score, so theme work is not expected to "
                   "move this page" % (ceiling_median, baseline_median))
    return out


def probe_for(inv, page, url):
    """The page's probe: built from its baseline mobile Samples once, then reused."""
    kept = inv.data.setdefault("ceilings", {}).get(page)
    if kept and kept.get("url") == url:
        return kept
    baseline = stats.members(inv.data["samples"], stats.BASELINE, page, url, "mobile", "control")
    if len(baseline) < stats.SAMPLES_PER_MEASUREMENT:
        raise Refused("no-baseline", "the %s page's baseline mobile Measurement holds %d of %d "
                      "Samples" % (page, len(baseline), stats.SAMPLES_PER_MEASUREMENT),
                      "Take it first with `sample --page %s --device mobile`; the probe is "
                      "built from what those Samples requested." % page)
    built = probe.build(_reports(inv, baseline), inv.data["store"]["url"],
                        inv.data["themes"]["control"]["asset_path"])
    built.update(url=url, built_from=[s["id"] for s in baseline], built_at=ledger.now())
    inv.data["ceilings"][page] = built
    inv.log("ceiling", "%s probe: %d patterns, %d protected" % (page, len(built["patterns"]),
                                                               len(built["protect"])))
    inv.save()
    return built
