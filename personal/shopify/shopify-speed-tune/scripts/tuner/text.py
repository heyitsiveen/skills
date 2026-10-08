"""Figures and names as the program prints them: on its fixed lines, and for people in the
plan and the report."""

import math
from datetime import datetime

COLUMNS = ("Performance", "LCP", "TBT", "CLS", "FCP", "Speed Index", "Accessibility")


def half_up(value, places=0):
    """`value` rounded half up, as people round (2.5 is 3), to `places` decimals: an int at 0."""
    factor = 10 ** places
    rounded = math.floor(value * factor + 0.5)
    return int(rounded) if places == 0 else rounded / factor


class Form:
    """How one metric prints: as a number with `line_unit` on the program's lines (`10157ms`),
    and as PageSpeed shows it, with `unit`, for people (`10.2 s`)."""

    def __init__(self, line, human, unit="", line_unit=""):
        self.number, self.human, self.unit, self.line_unit = line, human, unit, line_unit

    def line(self, value):
        return self.number(value) + self.line_unit

    def line_range(self, low, high):
        """`3567-5208ms`: one unit for the pair."""
        return "%s-%s%s" % (self.number(low), self.number(high), self.line_unit)

    def cell(self, median, low, high):
        """`10.2 s (9.4–11.0)`"""
        return "%s%s (%s–%s)" % (self.human(median), self.unit, self.human(low), self.human(high))


def _whole(value):
    return "%d" % half_up(value)


def _shift(value):
    return "%.3f" % value


def _grouped(value):
    return "{:,}".format(half_up(value))


def _seconds(value):
    return "%.1f" % half_up(value / 1000.0, 1)


# Scores are 0-100; times are ms, which people read in seconds, but for TBT.
FORMS = {
    "performance": Form(_whole, _whole),
    "lcp": Form(_whole, _seconds, " s", "ms"),
    "tbt": Form(_whole, _grouped, " ms", "ms"),
    "cls": Form(_shift, _shift),
    "fcp": Form(_whole, _seconds, " s", "ms"),
    "si": Form(_whole, _seconds, " s", "ms"),
    "accessibility": Form(_whole, _whole),
}


def cell(metric, median, low, high):
    """A Measurement's figure for people: its median, then its range."""
    return FORMS[metric].cell(median, low, high)


def score(figures):
    """A Performance Measurement as `50 (36–56)`, or – when it was not taken."""
    return "–" if figures is None else "%d (%d–%d)" % figures


def psi_table(kept, pages):
    """The developer's PageSpeed Insights mobile Performance scores beside the baseline medians,
    as the plan and the report print them: `kept` is the ledger's `psi` record."""
    lines = ["| Page | PageSpeed | Baseline | Gap |", "|---|---|---|---|"]
    for page in pages:
        if page in kept["scores"]:
            given, median = kept["scores"][page], kept["baseline"][page]
            lines.append("| %s | %d | %d | %+d |" % (page_name(page), given, median,
                                                     given - median))
    return lines


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


def page_name(page):
    """A page as people name it: `home` is Home."""
    return page.capitalize()
