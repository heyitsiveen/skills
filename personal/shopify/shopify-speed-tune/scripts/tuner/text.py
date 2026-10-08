"""Figures and names as the plan and the report print them for people."""

import math
from datetime import datetime

PAGE_NAMES = {"home": "Home", "collection": "Collection", "product": "Product"}
COLUMNS = ("Performance", "LCP", "TBT", "CLS", "FCP", "Speed Index", "Accessibility")


def half_up(value, places=0):
    """`value` rounded half up, as people round (2.5 is 3), to `places` decimals: an int at 0."""
    factor = 10 ** places
    rounded = math.floor(value * factor + 0.5)
    return int(rounded) if places == 0 else rounded / factor


def human(metric, value):
    """A figure as PageSpeed shows it: seconds for paint times, ms for TBT."""
    if metric in ("performance", "accessibility"):
        return "%d" % half_up(value)
    if metric == "cls":
        return "%.3f" % value
    if metric == "tbt":
        return "{:,}".format(half_up(value))
    return "%.1f" % half_up(value / 1000.0, 1)


def cell(metric, median, low, high):
    unit = {"tbt": " ms", "lcp": " s", "fcp": " s", "si": " s"}.get(metric, "")
    return "%s%s (%s–%s)" % (human(metric, median), unit, human(metric, low), human(metric, high))


def score(figures):
    """A Performance Measurement as `50 (36–56)`, or – when it was not taken."""
    return "–" if figures is None else "%d (%d–%d)" % figures


def when(stamp):
    """An ISO timestamp as `2026-10-08 06:00 (UTC+08:00)`."""
    try:
        moment = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return stamp or "?"
    offset = moment.strftime("%z")
    zone = " (UTC%s:%s)" % (offset[:3], offset[3:]) if offset else ""
    return moment.strftime("%Y-%m-%d %H:%M") + zone


def theme_name(theme):
    return "`%s` (#%s)" % (theme.get("name"), theme.get("id"))
