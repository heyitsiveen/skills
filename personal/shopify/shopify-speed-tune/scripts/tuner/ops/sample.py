"""sample: add Samples to one Measurement, by taking them or from report files.

Taking a Sample runs the pinned Lighthouse through pnpm's on-demand runner on
a fresh copy of the invocation's Chrome whose cookie jar holds the theme's
preview cookie for the store's host alone (tuner.browser). The page loads from
its own URL plus `?pb=0`, which keeps Shopify's preview bar out: never the
preview query parameter, never a redirect. The served theme is read back
before the first Sample and checked in every report.

With no --count, it takes Samples until the Measurement holds five, so a call
that is cut off part-way is finished by running it again. --report records
existing Lighthouse report files instead: the same checks, no Lighthouse run.
"""

import json
import os
import re

from tuner import browser, ledger, lighthouse, stats, storefront
from tuner.output import Failed, Refused, say
from tuner.probe import check as probe_check

ORDER = 30
PAGES = ("home", "collection", "product")
DEVICES = ("mobile", "desktop")
THEMES = ("control", "working")
# Rejected Samples a single call tolerates before it stops.
SPARE_ATTEMPTS = 2


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
    have = len(members(inv, args, url))
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
            if record(inv, args, url, theme, report, source="file") is None:
                return 1
    else:
        taken = take(inv, args, url, theme, wanted)
        if taken < wanted:
            raise Failed("samples-rejected", "%d of %d Samples taken; see the rejections above"
                         % (taken, wanted), "Run the same command again to continue.")

    done = members(inv, args, url)
    if len(done) == stats.SAMPLES_PER_MEASUREMENT:
        say("MEASUREMENT", stats.measurement_line(args.label, args.page, args.device, args.theme, done))
    return 0


def members(inv, args, url):
    return stats.members(inv.data["samples"], args.label, args.page, url, args.device, args.theme)


def take(inv, args, url, theme, wanted, probe=None):
    """Take Samples until `wanted` are recorded or the spare attempts run out.

    `probe` (the Ceiling probe: blocked patterns and the LCP image they spare)
    passes through to Lighthouse and to the check of every report.
    """
    cookie = preview(inv, theme, url)
    taken, attempts = 0, 0
    while taken < wanted and attempts < wanted + SPARE_ATTEMPTS:
        attempts += 1
        if attempt(inv, args, url, theme, cookie, probe=probe) is not None:
            taken += 1
    return taken


def preview(inv, theme, url):
    """The theme's preview cookie, once the page has been read back as that theme's."""
    data = inv.data
    chrome = data["tools"].get("chrome", {}).get("path", "")
    if not os.access(chrome, os.X_OK):
        raise Refused("no-chrome", "the invocation's Chrome is missing at %r" % chrome,
                      "It is downloaded by `start`; a finished invocation has none.")
    cookie = storefront.preview_cookie(data["store"]["url"], theme["id"])
    served = storefront.verify_theme(storefront.preview_url(url), cookie, theme["id"])
    if theme.get("asset_path") and served != theme["asset_path"]:
        raise Failed("preview-changed", "theme %s now serves %s, not %s"
                     % (theme["id"], served, theme["asset_path"]))
    return cookie


def attempt(inv, args, url, theme, cookie, probe=None, extra=None):
    """One Lighthouse run in a fresh copy of the invocation's Chrome: the recorded
    Sample, or None when its report was rejected."""
    data = inv.data
    workspace = data["workspace"]
    chrome = data["tools"]["chrome"]["path"]
    output = os.path.join(workspace, "raw-sample.json")
    if os.path.exists(output):
        os.remove(output)
    try:
        with browser.Chrome(workspace, chrome) as session:
            session.put_preview_cookie(data["store"]["url"], cookie)
            report = lighthouse.take(workspace, chrome, storefront.preview_url(url), args.device,
                                     session.port, output,
                                     blocked=probe["patterns"] if probe else ())
    except lighthouse.Rejected as rejection:
        reject(inv, args, rejection.reason)
        return None
    finally:
        if os.path.exists(output):
            os.remove(output)
    return record(inv, args, url, theme, report, source="lighthouse",
                  secrets=(cookie.split("=", 1)[1],), probe=probe, extra=extra)


def record(inv, args, url, theme, report, source, secrets=(), probe=None, extra=None):
    try:
        figures = lighthouse.check(report, storefront.preview_url(url), args.device,
                                   inv.data["tools"].get("lighthouse"), theme.get("asset_path"),
                                   blocked=probe["patterns"] if probe else ())
        if probe:
            probe_check(report, probe)
    except lighthouse.Rejected as rejection:
        reject(inv, args, rejection.reason)
        return None
    sample_id = "s%04d" % (len(inv.data["samples"]) + 1)
    os.makedirs(inv.file("samples"), exist_ok=True)
    stored = os.path.join("samples", sample_id + ".json")
    with open(inv.file(stored), "w", encoding="utf-8") as f:
        f.write(lighthouse.keepable(report, secrets))
    agent = (report.get("environment") or {}).get("hostUserAgent", "")
    build = re.search(r"HeadlessChrome/[\d.]+", agent)
    sample = {
        "id": sample_id, "label": args.label, "page": args.page, "url": url,
        "device": args.device, "theme": args.theme, "theme_id": theme["id"],
        "metrics": figures, "taken_at": report.get("fetchTime"), "source": source,
        "report": stored, "warnings": report.get("runWarnings") or [],
        "lighthouse": report.get("lighthouseVersion"),
        "chrome": build.group(0) if build else None,
        "axe": ((report.get("environment") or {}).get("credits") or {}).get("axe-core"),
    }
    sample.update(extra or {})
    inv.data["samples"].append(sample)
    inv.log("sample", "%s recorded (%s %s %s %s)" % (sample_id, args.label, args.page,
                                                    args.device, args.theme))
    inv.save()
    say("SAMPLE", stats.sample_line(sample))
    return sample


def reject(inv, args, reason):
    inv.log("sample", "rejected %s %s %s: %s" % (args.page, args.device, args.theme, reason))
    inv.save()
    say("SAMPLE", "rejected %s %s %s: %s" % (args.page, args.device, args.theme, reason))
