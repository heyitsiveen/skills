"""Measurement statistics: five Samples of one page, device and theme, as a median and a range.

A Measurement is never stored. It is computed from the ledger's Samples each
time it is read, so there is one source of truth for every figure.
"""

import math

from tuner.lighthouse import METRICS

SAMPLES_PER_MEASUREMENT = 5


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


def members(samples, label, page, url, device, theme):
    """The Samples that make up one Measurement, in the order they were taken.

    A discarded Sample (a pair's Control Sample whose Working Sample could not
    be taken) stays in the ledger for the record but counts in no Measurement.
    """
    return [s for s in samples
            if s["label"] == label and s["page"] == page and s["url"] == url
            and s["device"] == device and s["theme"] == theme and not s.get("discarded")]


BASELINE = "baseline"
# Each page on desktop once more, on the Working theme, after the Rounds.
FINAL = "final"
PAGE_ORDER = ("home", "collection", "product")
DEVICES = ("mobile", "desktop")


def measurements(data):
    """Every Measurement of the invocation as ((label, page, device, theme), samples).

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
    out = []
    for label, page, device, theme in keys:
        url = base + pages.get(page, "")
        out.append(((label, page, device, theme),
                    members(data.get("samples", []), label, page, url, device, theme)))
    return out


def sample_line(sample):
    figures = " | ".join("%s %s" % (m, show(m, sample["metrics"][m]))
                         for m in METRICS)
    return "%s %s %s %s %s | %s" % (sample["id"], sample["label"], sample["page"],
                                    sample["device"], sample["theme"], figures)


def measurement_line(label, page, device, theme, samples):
    head = "%s %s %s %s" % (label, page, device, theme)
    if len(samples) < SAMPLES_PER_MEASUREMENT:
        return "%s incomplete %d/%d" % (head, len(samples), SAMPLES_PER_MEASUREMENT)
    figures = summary(samples)
    parts = ["%s %s [%s]" % (m, show(m, figures[m][0]),
                             show_range(m, figures[m][1], figures[m][2]))
             for m in METRICS]
    return "%s n=%d | %s" % (head, len(samples), " | ".join(parts))
