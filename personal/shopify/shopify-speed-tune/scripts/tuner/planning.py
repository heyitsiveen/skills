"""The plan stop's numbers and rules: Ceilings and targets, the PageSpeed comparison,
the plan's items, its approval, and the refusal of any Round outside it.

Like every figure in the ledger, a Ceiling and a target are computed from their
Samples each time they are read, never stored.
"""

import json

from tuner import clock, stats
from tuner.output import Refused

CEILING = "ceiling"
PSI_TOLERANCE = 10  # points: the upper end of the run-to-run variance Shopify documents
ITEM_FIELDS = ("change", "cause", "effect")
# A known defect whose proven fix works only on top of another's (references/known-defects.md):
# an eager image needs the image snippet to read `lazy_loading: false`. While diagnose finds
# the second, every item fixing the first carries its fix too.
NEEDS = {"D2": "D1"}


def performance(inv, label, page):
    """(median, low, high) of the page's mobile Control theme Measurement, or None."""
    samples = stats.members(inv.data["samples"],
                            stats.Measurement.of(inv, label, page, "mobile", "control"))
    if len(samples) < stats.SAMPLES_PER_MEASUREMENT:
        return None
    median, low, high = stats.summary(samples)["performance"]
    return int(median), int(low), int(high)


def baseline_median(inv, page):
    """The page's baseline mobile Performance median, or a refusal while incomplete."""
    figures = performance(inv, stats.BASELINE, page)
    if figures is None:
        raise Refused("no-baseline", "the %s page's baseline mobile Measurement is not complete"
                      % page, "Take it with `sample --page %s --device mobile`." % page)
    return figures[0]


def ceiling(inv, page):
    """(median, low, high) of the page's Ceiling Measurement, or None while incomplete."""
    return performance(inv, CEILING, page)


def target(inv, page):
    """The lower of the requested score and the page's own Ceiling, or None."""
    found = ceiling(inv, page)
    if found is None:
        return None
    return min(int(inv.data["requested_score"]), found[0])


def ceiling_line(inv, page):
    found = ceiling(inv, page)
    if found is None:
        return None
    return "%s ceiling=%d requested=%d target=%d" % (page, found[0], inv.data["requested_score"],
                                                     target(inv, page))


def pages_ready(inv):
    """Refuse unless every page has its baseline and its Ceiling."""
    for page in stats.PAGE_ORDER:
        baseline_median(inv, page)
        if ceiling(inv, page) is None:
            raise Refused("no-ceiling", "the %s page's Ceiling Measurement is not complete" % page,
                          "Measure it with `ceiling --page %s`." % page)


# -- the PageSpeed comparison ---------------------------------------------------

def record_psi(inv, scores):
    """Keep the developer's PageSpeed Insights mobile Performance scores beside the baseline
    medians."""
    for page, score in scores.items():
        if not 0 <= score <= 100:
            raise Refused("bad-score", "a Performance score from PageSpeed Insights is 0-100, not "
                          "%d (%s)" % (score, page))
    medians = {page: baseline_median(inv, page) for page in scores}
    inv.data["psi"] = {"scores": dict(scores), "baseline": medians, "recorded_at": clock.now()}
    inv.log("psi", "PageSpeed %s" % ", ".join("%s %d" % (p, s) for p, s in scores.items()))
    inv.save()


def psi_lines(inv):
    """([PSI line text], [WARN line text]) for the recorded comparison."""
    kept = inv.data.get("psi")
    if not kept:
        return [], []
    lines, warnings = [], []
    for page in stats.PAGE_ORDER:
        if page not in kept["scores"]:
            continue
        score, median = kept["scores"][page], kept["baseline"][page]
        gap = score - median
        lines.append("%s pagespeed=%d baseline=%d gap=%s" % (page, score, median,
                                                             "%+d" % gap if gap else "0"))
        if abs(gap) > PSI_TOLERANCE:
            warnings.append(
                "psi-gap %s: PageSpeed's %d is %d points %s this skill's baseline median of %d. "
                "Past %d points the gap is more than run-to-run variance, so the PageSpeed "
                "screenshot after going live may not match this skill's report"
                % (page, score, abs(gap), "above" if gap > 0 else "below", median, PSI_TOLERANCE))
    return lines, warnings


# -- the plan -----------------------------------------------------------------

def found_defects(inv):
    checked = inv.data.get("defects")
    if checked is None:
        raise Refused("no-diagnosis", "the store has not been diagnosed",
                      "Run `diagnose` first; the plan puts its known defects first.")
    return [r["id"] for r in checked.get("results", []) if r["state"] == "found"]


def unstated(item):
    """The first of its change, cause and expected effect an item does not state, or None."""
    return next((field for field in ITEM_FIELDS
                 if not isinstance(item.get(field), str) or not item[field].strip()), None)


def read_items(path):
    try:
        with open(path, encoding="utf-8") as f:
            items = json.load(f)
    except (OSError, ValueError) as e:
        raise Refused("bad-plan", "%s cannot be read as JSON: %s" % (path, e))
    if isinstance(items, dict):
        items = items.get("items")
    if not isinstance(items, list) or not items:
        raise Refused("bad-plan", "%s holds no plan items: give a JSON list of items" % path)
    return items


def record_plan(inv, items):
    """Check the draft items, put known defects first, number them P1… and keep them."""
    if (inv.data.get("plan") or {}).get("approved_at"):
        raise Refused("plan-approved", "the plan was approved at %s and is final"
                      % inv.data["plan"]["approved_at"])
    pages_ready(inv)
    found = found_defects(inv)
    checked = []
    for n, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise Refused("bad-plan", "item %d is not an object" % n)
        field = unstated(item)
        if field:
            raise Refused("bad-plan", "item %d states no %s" % (n, field),
                          "Every item states its change, its pages, the cause it addresses "
                          "and its expected effect.")
        pages = item.get("pages")
        if not isinstance(pages, list) or not pages or \
                any(p not in stats.PAGE_ORDER for p in pages) or len(set(pages)) != len(pages):
            raise Refused("bad-plan", "item %d's pages must be some of %s, not %r"
                          % (n, ", ".join(stats.PAGE_ORDER), pages))
        named = item.get("defects") or []
        if not isinstance(named, list):
            raise Refused("bad-plan", "item %d's defects must be a list of ids like D2" % n)
        for entry in named:
            if entry not in found:
                raise Refused("bad-plan", "item %d names %s, which diagnose did not find" % (n, entry),
                              "Name only defects with a `DEFECT … found` line.")
            needed = NEEDS.get(entry)
            if needed in found and needed not in named:
                raise Refused("bad-plan", "item %d fixes %s but not %s, which %s's fix needs"
                              % (n, entry, needed, entry),
                              "A Round measures its item alone on top of the Rounds already "
                              "kept, and an earlier item carrying %s may be removed: add %s to "
                              "item %d's defects and its fix to its change." % (needed, needed, n))
        checked.append({
            "change": item["change"].strip(), "cause": item["cause"].strip(),
            "effect": item["effect"].strip(),
            "pages": [p for p in stats.PAGE_ORDER if p in pages], "defects": list(named),
        })
    ordered = [i for i in checked if i["defects"]] + [i for i in checked if not i["defects"]]
    for n, item in enumerate(ordered, 1):
        item["id"] = "P%d" % n
    inv.data["plan"] = {"items": ordered, "recorded_at": clock.now(), "approved_at": None}
    inv.log("plan", "draft plan recorded: %d items" % len(ordered))
    inv.save()
    return ordered


def unplanned_defects(inv):
    planned = {d for item in (inv.data.get("plan") or {}).get("items", []) for d in item["defects"]}
    return [d for d in found_defects(inv) if d not in planned]


def item_line(item):
    known = " known=%s" % ",".join(item["defects"]) if item["defects"] else ""
    return "item %s%s pages=%s | change: %s | cause: %s | effect: %s" % (
        item["id"], known, ",".join(item["pages"]), item["change"], item["cause"], item["effect"])


def approve(inv):
    plan = inv.data.get("plan")
    if not plan or not plan.get("items"):
        raise Refused("no-plan", "no plan is recorded", "Record it with `plan --items <file>`.")
    if plan.get("approved_at"):
        return plan
    pages_ready(inv)
    plan["approved_at"] = clock.now()
    inv.log("plan", "plan approved: %s" % ", ".join(i["id"] for i in plan["items"]))
    inv.save()
    return plan


def require_approved(inv):
    plan = inv.data.get("plan") or {}
    if not plan.get("approved_at"):
        raise Refused("plan-not-approved", "no approved plan: a Round uses only an item of the "
                      "plan the developer approved", "Approve it with `plan --approve`.")
    return plan


def unused(inv):
    """The approved plan's items no Round has used yet, in the plan's order."""
    used = {r["item"] for r in inv.data.get("rounds", [])}
    return [i for i in (inv.data.get("plan") or {}).get("items", []) if i["id"] not in used]


def claim(inv, item_id=None):
    """The approved plan's item for a new Round, or a refusal: no Round may use an
    item outside the plan, or an item a Round already used. With no id, the first
    unused item."""
    plan = require_approved(inv)
    if item_id is None:
        left = unused(inv)
        if not left:
            raise Refused("plan-exhausted", "every item of the approved plan was used")
        return left[0]
    item = next((i for i in plan["items"] if i["id"] == item_id), None)
    if item is None:
        raise Refused("unplanned-item", "%s is not in the approved plan (%s)"
                      % (item_id, ", ".join(i["id"] for i in plan["items"])))
    used = next((r for r in inv.data.get("rounds", []) if r["item"] == item_id), None)
    if used is not None:
        raise Refused("item-used", "%s was already used by Round %d" % (item_id, used["n"]))
    return item


# -- status -------------------------------------------------------------------

def status_lines(inv):
    """[(tag, text)]: what the plan stop has recorded, for `status`."""
    out = []
    for page in stats.PAGE_ORDER:
        if page in inv.data.get("pages", {}):
            line = ceiling_line(inv, page)
            if line:
                out.append(("CEILING", line))
    plan = inv.data.get("plan")
    if plan:
        used = {r["item"] for r in inv.data.get("rounds", [])}
        out.append(("PLAN", "%s items=%d used=%d" % (
            "approved" if plan.get("approved_at") else "draft", len(plan["items"]),
            len(used & {i["id"] for i in plan["items"]}))))
    lines, _ = psi_lines(inv)
    out += [("PSI", line) for line in lines]
    return out
