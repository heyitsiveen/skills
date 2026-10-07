"""report: write the baseline report into the invocation's folder.

Every figure comes from the ledger: each page's Measurement on the Control
theme, mobile and desktop, as a median with its range, plus the Lighthouse and
Chrome versions that took every Sample.
"""

import math
from datetime import datetime

from tuner import ledger, stats, tools
from tuner.output import say

ORDER = 85
PAGE_NAMES = {"home": "Home", "collection": "Collection", "product": "Product"}
COLUMNS = ("Performance", "LCP", "TBT", "CLS", "FCP", "Speed Index", "Accessibility")


def register(sub):
    p = sub.add_parser("report", help="write the baseline report into the invocation's folder")
    p.add_argument("--invocation", help="a finished invocation of this repo, by id")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.find(args.invocation)
    path = inv.file("report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(inv))
    inv.log("report", "baseline report written")
    inv.save()
    say("REPORT", path)
    return 0


def _half_up(value, places=0):
    factor = 10 ** places
    return math.floor(value * factor + 0.5) / factor


def human(metric, value):
    """A figure as PageSpeed shows it: seconds for paint times, ms for TBT."""
    if metric in ("performance", "accessibility"):
        return "%d" % _half_up(value)
    if metric == "cls":
        return "%.3f" % value
    if metric == "tbt":
        return "{:,}".format(int(_half_up(value)))
    return "%.1f" % _half_up(value / 1000.0, 1)


def cell(metric, median, low, high):
    unit = {"tbt": " ms", "lcp": " s", "fcp": " s", "si": " s"}.get(metric, "")
    return "%s%s (%s–%s)" % (human(metric, median), unit, human(metric, low), human(metric, high))


def render(inv):
    data = inv.data
    store = data["store"]
    control = data["themes"].get("control", {})
    published = store.get("published_theme", {})
    samples = data.get("samples", [])
    axe = sorted({s["axe"] for s in samples if s.get("axe")})
    lines = [
        "# Speed baseline: %s" % store["url"],
        "",
        "| | |",
        "|---|---|",
        "| Store | %s (`%s`) |" % (store["url"], store["myshopify"]),
        "| Invocation | `%s`, started %s |" % (inv.id, when(data.get("created_at"))),
        "| Requested score | %s |" % data.get("requested_score"),
        "| Measured on | the Control theme `%s` (#%s), an unpublished copy of the published "
        "theme `%s` (#%s) |" % (control.get("name"), control.get("id"), published.get("name"),
                                published.get("id")),
        "| Tools | Lighthouse %s%s on Chrome for Testing %s |" % (
            data["tools"].get("lighthouse", tools.LIGHTHOUSE),
            " (axe-core %s)" % ", ".join(axe) if axe else "",
            data["tools"].get("chrome", {}).get("build", tools.CHROME_BUILD)),
        "",
        "## Pages",
        "",
    ]
    for page in stats.PAGE_ORDER:
        if page in data.get("pages", {}):
            lines.append("- %s: %s" % (PAGE_NAMES[page], inv.page_url(page)))
    lines += [
        "",
        "## Baseline",
        "",
        "Each figure is the median of five Samples, with their range in brackets. Mobile is "
        "Lighthouse's emulated phone with simulated throttling; desktop is its desktop preset. "
        "The Control theme is measured through its preview cookie on the plain page URL, so "
        "every Sample also loads Shopify's preview bar and a page rendered without the "
        "storefront cache: these figures read lower than the published store's.",
        "",
        "| Page | Device | %s |" % " | ".join(COLUMNS),
        "|---|---|%s" % ("---|" * len(COLUMNS)),
    ]
    for (label, page, device, theme), members in stats.measurements(data):
        if (label, theme) != (stats.BASELINE, "control"):
            continue
        if len(members) < stats.SAMPLES_PER_MEASUREMENT:
            lines.append("| %s | %s | not measured (%d of %d Samples) |"
                         % (PAGE_NAMES[page], device, len(members), stats.SAMPLES_PER_MEASUREMENT))
            continue
        figures = stats.summary(members)
        cells = [cell(m, *figures[m]) for m in stats.METRICS]
        lines.append("| %s | %s | %s |" % (PAGE_NAMES[page], device, " | ".join(cells)))
    lines += ["", "## What stays", ""]
    working = data["themes"].get("working")
    if working:
        lines.append("- The Working theme `%s` (#%s), unpublished. It holds every kept change "
                     "and is the theme to publish." % (working.get("name"), working.get("id")))
    if data["repo"].get("branch"):
        lines.append("- The branch `%s` in %s." % (data["repo"]["branch"], data["repo"]["root"]))
    lines.append("- The Control theme is deleted at cleanup, and Chrome for Testing is removed.")
    warnings = {}
    for s in samples:
        for warning in s.get("warnings", []):
            key = (s["page"], s["device"], warning)
            warnings[key] = warnings.get(key, 0) + 1
    if warnings:
        lines += ["", "## Lighthouse warnings", ""]
        for (page, device, warning), count in sorted(warnings.items(), key=page_order):
            lines.append("- %s %s, %d Sample%s: %s" % (PAGE_NAMES.get(page, page), device, count,
                                                      "" if count == 1 else "s", warning))
    return "\n".join(lines) + "\n"


def page_order(item):
    (page, device, warning), _ = item
    rank = stats.PAGE_ORDER.index(page) if page in stats.PAGE_ORDER else len(stats.PAGE_ORDER)
    return rank, stats.DEVICES.index(device), warning


def when(stamp):
    """An ISO timestamp as `2026-10-08 06:00 (UTC+08:00)`."""
    try:
        moment = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return stamp or "?"
    offset = moment.strftime("%z")
    zone = " (UTC%s:%s)" % (offset[:3], offset[3:]) if offset else ""
    return moment.strftime("%Y-%m-%d %H:%M") + zone
