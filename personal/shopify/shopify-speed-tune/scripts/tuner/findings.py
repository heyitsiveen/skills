"""What the baseline Samples' own Lighthouse reports say, read without another Sample.

Every figure here is a median over a page's five baseline mobile Samples. The
reports are already in the invocation's folder, so diagnosis costs nothing.

- `costs` is the app and tag cost table, from Lighthouse's third-party summary.
  Shopify app extensions, which Lighthouse files under its "Shopify" row, get a
  row of their own named by their extension folder.
- `lcp_line`, `render_blocking_line`, `layout_shift_line` and `long_tasks_line`
  are one-line digests of the LCP breakdown, the render-blocking requests, the
  layout shifts and the long tasks, with every request named by its `Owners`:
  the theme, the page's own HTML, Shopify, an app, or a third-party host.
"""

import json
import re
from urllib.parse import urlsplit

from tuner import probe, stats
from tuner.output import Refused
from tuner.text import PAGE_NAMES, half_up

EXTENSION = re.compile(r"^https://cdn\.shopify\.com/extensions/[^/]+/([^/]+?)(?:-\d+)?/")
SUBPARTS = (("timeToFirstByte", "time to first byte"),
            ("resourceLoadDelay", "resource load delay"),
            ("resourceLoadDuration", "resource load duration"),
            ("elementRenderDelay", "element render delay"))
SHOWN = 6  # owners or elements a line names


def baseline(inv, page):
    """The page's five baseline mobile Samples with their stored reports."""
    samples = stats.members(inv.data["samples"], stats.Measurement.baseline(inv, page))
    if len(samples) < stats.SAMPLES_PER_MEASUREMENT:
        raise Refused("no-baseline", "the %s page's baseline mobile Measurement holds %d of %d "
                      "Samples" % (page, len(samples), stats.SAMPLES_PER_MEASUREMENT),
                      "Take it with `sample --page %s --device mobile` first." % page)
    out = []
    for s in samples:
        with open(inv.file(s["report"]), encoding="utf-8") as f:
            out.append((s, json.load(f)))
    return out


def _items(report, audit_id):
    audit = (report.get("audits") or {}).get(audit_id) or {}
    return (audit.get("details") or {}).get("items") or []


def _median(values):
    return stats.median(values) if values else 0


def most_common(values):
    """The most frequent value; a tie goes to the one seen first."""
    return max(values, key=lambda v: (values.count(v), -values.index(v))) if values else None


# -- the app and tag cost table ----------------------------------------------

def _entities(report):
    """{row name: (main-thread ms, transfer bytes)} for one report."""
    rows = {}
    for item in _items(report, "third-parties-insight"):
        name = item.get("entity")
        if not name:
            continue
        time, size = item.get("mainThreadTime") or 0, item.get("transferSize") or 0
        if name == "Shopify":
            for sub in ((item.get("subItems") or {}).get("items") or []):
                found = EXTENSION.match(sub.get("url") or "")
                if not found:
                    continue
                app = "%s (Shopify app)" % found.group(1)
                was = rows.get(app, (0, 0))
                sub_time, sub_size = sub.get("mainThreadTime") or 0, sub.get("transferSize") or 0
                rows[app] = (was[0] + sub_time, was[1] + sub_size)
                time, size = time - sub_time, size - sub_size
        was = rows.get(name, (0, 0))
        rows[name] = (was[0] + max(time, 0), was[1] + max(size, 0))
    return rows


def costs(reports_by_page):
    """The cost table: [(name, {page: (ms, bytes) | None})], costliest first.

    Each cell is the median over the page's Samples, a Sample without the row
    counting as zero; None means no Sample of that page loaded anything from it.
    """
    per_page = {page: [_entities(r) for r in reports] for page, reports in reports_by_page.items()}
    names = sorted({name for rows in per_page.values() for sample in rows for name in sample})
    table = []
    for name in names:
        cells = {}
        for page, samples in per_page.items():
            present = [s[name] for s in samples if name in s]
            if not present:
                cells[page] = None
                continue
            padded = present + [(0, 0)] * (len(samples) - len(present))
            cells[page] = (_median([c[0] for c in padded]), _median([c[1] for c in padded]))
        table.append((name, cells))
    table.sort(key=lambda row: (-max((c[0] for c in row[1].values() if c), default=0),
                                -max((c[1] for c in row[1].values() if c), default=0), row[0]))
    return table


def cost_cell(cell):
    if cell is None:
        return "-"
    time, size = cell
    kib = size / 1024.0
    return "%d ms %s KiB" % (half_up(time), ("%d" % half_up(kib)) if kib >= 0.5 else "<1")


def cost_line(name, cells, pages):
    return "%s | %s" % (name, " | ".join("%s %s" % (page, cost_cell(cells.get(page)))
                                         for page in pages))


def cost_text(cell):
    """A cell as people read it: `114 ms · 159 KiB`, or – when the page never loaded it."""
    return "–" if cell is None else cost_cell(cell).replace(" ms ", " ms · ")


def cost_table(table, pages):
    """The cost table as the plan and the report print it, with what its figures are."""
    return ["| App or tag | %s |" % " | ".join(PAGE_NAMES[p] for p in pages),
            "|---|%s" % ("---|" * len(pages))] + [
        "| %s | %s |" % (name, " | ".join(cost_text(cells.get(p)) for p in pages))
        for name, cells in table] + [
        "",
        "Main-thread time on this Mac without throttling, then transfer size: the median of each "
        "page's five baseline Samples, from Lighthouse's third-party summary. – means the page "
        "never loaded it. The skill leaves every app and tag as the merchant set them; these "
        "figures are for the merchant."]


# -- one-line digests of the other findings -------------------------------------

class Owners:
    """Names who owns a request: the theme, the page's own HTML, Shopify, an app, or a host."""

    def __init__(self, store_url, asset_path, page_url):
        self.host = urlsplit(store_url).hostname
        self.theme = "https://%s%s" % (self.host, asset_path)
        self.page = page_url

    def __call__(self, url):
        if not isinstance(url, str) or "://" not in url:
            return "unattributable"
        app = EXTENSION.match(url)
        if app:
            return "app %s" % app.group(1)
        parts = urlsplit(url)
        if parts.hostname == "cdn.shopify.com":
            return "Shopify"
        if parts.hostname != self.host:
            return parts.hostname or "unattributable"
        if url.startswith(self.theme):
            return "theme"
        if url.split("?")[0] == self.page.split("?")[0]:
            return "the page's HTML"
        if "web-pixels" in parts.path or parts.path.startswith("/cdn/wpm/"):
            return "Shopify web pixels"
        found = re.match(r"/cdn/shopifycloud/([^/]+)/", parts.path)
        return "Shopify %s" % found.group(1) if found else "Shopify"


def _file(url):
    return urlsplit(url).path.rsplit("/", 1)[-1]


def _ms(value):
    return "%d ms" % half_up(value)


def lcp_line(reports):
    found = [probe.lcp(r) for r in reports]
    kind = most_common([f["kind"] for f in found])
    if kind == "none":
        return "lcp: no largest paint in the reports"
    same = [f for f in found if f["kind"] == kind]
    what = kind
    urls = [f["url"] for f in same if f["url"]]
    if kind == "image":
        what = "image %s" % (probe.place(most_common(urls)) if urls else "(URL unknown)")
    element = most_common([f["selector"] for f in same if f["selector"]]) or "?"
    parts = ["lcp: %s, element %s, in %d of %d Samples" % (what, element, len(same), len(reports))]
    if kind == "image" and sum(1 for r in reports if probe.lazy_lcp(r)) * 2 >= len(reports):
        parts[0] += "; it waits for a lazy-loader script"
    durations = {}
    for report in reports:
        for item in _items(report, "lcp-breakdown-insight"):
            if item.get("type") == "table":
                for row in item.get("items") or []:
                    durations.setdefault(row.get("subpart"), []).append(row.get("duration") or 0)
    shown = ["%s %s" % (label, _ms(_median(durations[key]))) for key, label in SUBPARTS
             if key in durations]
    if shown:
        parts.append("%s (medians, unthrottled)" % ", ".join(shown))
    failed = []
    for report in reports:
        for item in _items(report, "lcp-discovery-insight"):
            if item.get("type") == "checklist":
                for check in (item.get("items") or {}).values():
                    if check.get("value") is False and check.get("label") not in failed:
                        failed.append(check.get("label"))
    if failed:
        parts.append("discovery fails: %s" % "; ".join(failed))
    return " | ".join(parts)


def render_blocking_line(reports, owners):
    savings = {"FCP": [], "LCP": []}
    largest = {}
    for report in reports:
        audit = (report.get("audits") or {}).get("render-blocking-insight") or {}
        for metric in savings:
            savings[metric].append(((audit.get("metricSavings") or {}).get(metric)) or 0)
        for item in _items(report, "render-blocking-insight"):
            url = item.get("url") or ""
            key = url.split("?")[0]
            largest[key] = max(largest.get(key, 0), item.get("totalBytes") or 0)
    if not largest:
        return "render-blocking: none"
    groups = {}
    for url, size in largest.items():
        groups.setdefault(owners(url), []).append((size, url))
    ordered = sorted(groups.items(), key=lambda g: (-len(g[1]), g[0]))
    shown = []
    for owner, members in ordered:
        text = "%s %d (%d KiB)" % (owner, len(members), half_up(sum(s for s, _ in members) / 1024.0))
        if owner == "theme":
            text += ": %s" % ", ".join(_file(u) for _, u in sorted(members, reverse=True)[:SHOWN])
        shown.append(text)
    return "render-blocking: %d requests hold the first paint (median saving FCP %s, LCP %s); %s" % (
        len(largest), _ms(_median(savings["FCP"])), _ms(_median(savings["LCP"])), "; ".join(shown))


def layout_shift_line(reports):
    cls = [((r.get("audits") or {}).get("cumulative-layout-shift") or {}).get("numericValue") or 0
           for r in reports]
    elements = {}
    for report in reports:
        seen = {}
        for item in _items(report, "layout-shifts"):
            selector = ((item.get("node") or {}).get("selector") or "?").split(" > ")[-1]
            causes = [s.get("cause") for s in ((item.get("subItems") or {}).get("items") or [])
                      if s.get("cause")]
            score, was = item.get("score") or 0, seen.get(selector, (0, []))
            seen[selector] = (max(score, was[0]), sorted(set(was[1] + causes)))
        for selector, (score, causes) in seen.items():
            kept = elements.setdefault(selector, {"scores": [], "causes": set()})
            kept["scores"].append(score)
            kept["causes"].update(causes)
    text = "layout-shift: CLS %.3f (median)" % _median(cls)
    if not elements:
        return text + "; no element shifted"
    ranked = sorted(elements.items(), key=lambda e: (-max(e[1]["scores"]), e[0]))[:SHOWN]
    return text + "; " + ", ".join(
        "%s %.3f in %d of %d%s" % (selector, max(e["scores"]), len(e["scores"]), len(reports),
                                   " (%s)" % "; ".join(sorted(e["causes"])) if e["causes"] else "")
        for selector, e in ranked)


def long_tasks_line(reports, owners):
    per_sample = []
    for report in reports:
        totals = {}
        for item in _items(report, "long-tasks"):
            owner = owners(item.get("url"))
            totals[owner] = totals.get(owner, 0) + (item.get("duration") or 0)
        per_sample.append(totals)
    names = {owner for totals in per_sample for owner in totals}
    medians = {owner: _median([totals.get(owner, 0) for totals in per_sample]) for owner in names}
    ranked = sorted(medians.items(), key=lambda m: (-m[1], m[0]))[:SHOWN]
    if not ranked:
        return "long-tasks: none"
    return "long-tasks (median ms per Sample, simulated): %s" % ", ".join(
        "%s %d" % (owner, half_up(ms)) for owner, ms in ranked)
