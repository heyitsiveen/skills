"""Measurement statistics: five Samples of one page, device and theme, as a median and a range.

A Measurement is never stored. It is computed from the ledger's Samples each
time it is read, so there is one source of truth for every figure.
"""

import math
from collections import namedtuple

from tuner.lighthouse import METRICS

SAMPLES_PER_MEASUREMENT = 5


class Measurement(namedtuple("Measurement", "label page device theme url")):
    """Which Measurement: its label (baseline, ceiling, round-<n> or final), page, device and
    theme, and the page's URL, so that only Samples of the page as it is now count."""
    __slots__ = ()

    @classmethod
    def of(cls, inv, label, page, device, theme):
        """The Measurement of `page` at its current URL."""
        return cls(label, page, device, theme, inv.page_url(page))

    @classmethod
    def baseline(cls, inv, page, device="mobile"):
        """The page's baseline: the Control theme, measured before any Round."""
        return cls.of(inv, BASELINE, page, device, "control")

    def holds(self, sample):
        """True when `sample` counts in this Measurement."""
        return (sample["label"], sample["page"], sample["device"], sample["theme"],
                sample["url"]) == tuple(self) and not sample.get("discarded")

    def __str__(self):
        return "%s %s %s %s" % (self.label, self.page, self.device, self.theme)


def median(values):
    ordered = sorted(values)
    n = len(ordered)
    middle = n // 2
    if n % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def summary(samples):
    """{metric: (median, low, high)} over the Samples' metrics."""
    out = {}
    for metric in METRICS:
        values = [s["metrics"][metric] for s in samples]
        out[metric] = (median(values), min(values), max(values))
    return out


def _half_up(value):
    return int(math.floor(value + 0.5))


def show(metric, value):
    """One figure the way every line and report prints it."""
    if metric == "cls":
        return "%.3f" % value
    if metric in ("performance", "accessibility"):
        return str(_half_up(value))
    return "%dms" % _half_up(value)


def show_range(metric, low, high):
    low_text, high_text = show(metric, low), show(metric, high)
    if metric not in ("cls", "performance", "accessibility"):
        low_text = low_text[:-2]  # one unit for the pair: 3567-5208ms
    return "%s-%s" % (low_text, high_text)


def members(samples, measurement):
    """The Samples that make up one Measurement, in the order they were taken.

    A discarded Sample (a pair's Control Sample whose Working Sample could not
    be taken) stays in the ledger for the record but counts in no Measurement.
    """
    return [s for s in samples if measurement.holds(s)]


BASELINE = "baseline"
# Each page on desktop once more, on the Working theme, after the Rounds.
FINAL = "final"
PAGE_ORDER = ("home", "collection", "product")
DEVICES = ("mobile", "desktop")


def measurements(data):
    """Every Measurement of the invocation as (Measurement, samples).

    The baseline's six (each page on the Control theme, mobile and desktop) are
    always listed, empty or not; any other Measurement follows in the order its
    first Sample was taken. Only Samples of a page's current URL count.
    """
    base = data["store"]["url"].rstrip("/")
    pages = data.get("pages", {})
    keys = [(BASELINE, page, device, "control")
            for page in PAGE_ORDER if page in pages for device in DEVICES]
    for s in data.get("samples", []):
        key = (s["label"], s["page"], s["device"], s["theme"])
        if key not in keys:
            keys.append(key)
    found = [Measurement(*key, url=base + pages.get(key[1], "")) for key in keys]
    return [(m, members(data.get("samples", []), m)) for m in found]


def sample_line(sample):
    figures = " | ".join("%s %s" % (m, show(m, sample["metrics"][m]))
                         for m in METRICS)
    return "%s %s %s %s %s | %s" % (sample["id"], sample["label"], sample["page"],
                                    sample["device"], sample["theme"], figures)


def measurement_line(measurement, samples):
    head = str(measurement)
    if len(samples) < SAMPLES_PER_MEASUREMENT:
        return "%s incomplete %d/%d" % (head, len(samples), SAMPLES_PER_MEASUREMENT)
    figures = summary(samples)
    parts = ["%s %s [%s]" % (m, show(m, figures[m][0]),
                             show_range(m, figures[m][1], figures[m][2]))
             for m in METRICS]
    return "%s n=%d | %s" % (head, len(samples), " | ".join(parts))
