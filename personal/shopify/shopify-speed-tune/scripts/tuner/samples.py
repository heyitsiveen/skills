"""Samples: taking one with the pinned Lighthouse, or recording one from a report file.

Taking a Sample runs the pinned Lighthouse through pnpm's on-demand runner on
a fresh copy of the invocation's Chrome whose cookie jar holds the theme's
preview cookie for the store's host alone (tuner.browser). The page loads from
its own URL plus `?pb=0`, which keeps Shopify's preview bar out: never the
preview query parameter, never a redirect. The served theme is read back
before the first Sample and checked in every report, and a report is recorded
only once it passes every check in tuner.lighthouse.

Every Sample belongs to one Measurement (a stats.Measurement), which says what
it is of: the page at its URL, the device and the theme.
"""

import os
import re

from tuner import browser, lighthouse, stats, storefront
from tuner.output import Failed, Refused, say
from tuner.probe import check as probe_check

# Rejected Samples a single call tolerates before it stops.
SPARE_ATTEMPTS = 2


def members(inv, measurement):
    return stats.members(inv.data["samples"], measurement)


def take(inv, measurement, theme, wanted, probe=None):
    """Take Samples until `wanted` are recorded or the spare attempts run out.

    `probe` (the Ceiling probe: blocked patterns and the LCP image they spare)
    passes through to Lighthouse and to the check of every report.
    """
    cookie = preview(inv, theme, measurement.url)
    taken, attempts = 0, 0
    while taken < wanted and attempts < wanted + SPARE_ATTEMPTS:
        attempts += 1
        if attempt(inv, measurement, theme, cookie, probe=probe) is not None:
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


def attempt(inv, measurement, theme, cookie, probe=None, extra=None):
    """One Sample, in a fresh copy of the invocation's Chrome: the recorded Sample, or None
    when its report was rejected."""
    data = inv.data
    workspace = data["workspace"]
    chrome = data["tools"]["chrome"]["path"]
    output = os.path.join(workspace, "raw-sample.json")
    if os.path.exists(output):
        os.remove(output)
    try:
        with browser.Chrome(workspace, chrome) as session:
            session.put_preview_cookie(data["store"]["url"], cookie)
            report = lighthouse.take(workspace, chrome, storefront.preview_url(measurement.url),
                                     measurement.device, session.port, output,
                                     blocked=probe["patterns"] if probe else ())
    except lighthouse.Rejected as rejection:
        reject(inv, measurement, rejection.reason)
        return None
    finally:
        if os.path.exists(output):
            os.remove(output)
    return record(inv, measurement, theme, report, source="lighthouse",
                  secrets=(cookie.split("=", 1)[1],), probe=probe, extra=extra)


def record(inv, measurement, theme, report, source, secrets=(), probe=None, extra=None):
    """Record `report` as a Sample of `measurement` once it passes every check: the Sample,
    or None when the report was rejected."""
    m = measurement
    try:
        figures = lighthouse.check(report, storefront.preview_url(m.url), m.device,
                                   inv.data["tools"].get("lighthouse"), theme.get("asset_path"),
                                   blocked=probe["patterns"] if probe else ())
        if probe:
            probe_check(report, probe)
    except lighthouse.Rejected as rejection:
        reject(inv, m, rejection.reason)
        return None
    sample_id = "s%04d" % (len(inv.data["samples"]) + 1)
    os.makedirs(inv.file("samples"), exist_ok=True)
    stored = os.path.join("samples", sample_id + ".json")
    with open(inv.file(stored), "w", encoding="utf-8") as f:
        f.write(lighthouse.keepable(report, secrets))
    agent = (report.get("environment") or {}).get("hostUserAgent", "")
    build = re.search(r"HeadlessChrome/[\d.]+", agent)
    sample = {
        "id": sample_id, "label": m.label, "page": m.page, "url": m.url,
        "device": m.device, "theme": m.theme, "theme_id": theme["id"],
        "metrics": figures, "taken_at": report.get("fetchTime"), "source": source,
        "report": stored, "warnings": report.get("runWarnings") or [],
        "lighthouse": report.get("lighthouseVersion"),
        "chrome": build.group(0) if build else None,
        "axe": ((report.get("environment") or {}).get("credits") or {}).get("axe-core"),
    }
    sample.update(extra or {})
    inv.data["samples"].append(sample)
    inv.log("sample", "%s recorded (%s)" % (sample_id, m))
    inv.save()
    say("SAMPLE", stats.sample_line(sample))
    return sample


def reject(inv, measurement, reason):
    m = measurement
    inv.log("sample", "rejected %s %s %s: %s" % (m.page, m.device, m.theme, reason))
    inv.save()
    say("SAMPLE", "rejected %s %s %s: %s" % (m.page, m.device, m.theme, reason))
