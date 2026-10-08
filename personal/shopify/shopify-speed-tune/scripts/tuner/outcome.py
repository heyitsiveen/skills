"""What an invocation came to, read from its ledger for the report: each page's
Performance score before and after, against its target and its Ceiling, and
desktop at the start and the end; why a removed Round was removed; and, for
each missed target, the reason and next plan written for it.

Like every figure in the ledger, each is computed from its Samples when read.
Nothing here refuses a missing figure: one never measured is None, so the
report can be written whichever step the invocation stopped in.
"""

import json

from tuner import clock, planning, rounds, stats
from tuner.output import Refused


def figures(inv, label, page, device, theme):
    """(median, low, high) of a complete Measurement's Performance score, or None."""
    samples = stats.members(inv.data.get("samples", []),
                            stats.Measurement.of(inv, label, page, device, theme))
    if len(samples) < stats.SAMPLES_PER_MEASUREMENT:
        return None
    median, low, high = stats.summary(samples)["performance"]
    return int(median), int(low), int(high)


def rounds_ran(inv):
    """True once the developer approved the plan: from then on a target can be missed."""
    return bool((inv.data.get("plan") or {}).get("approved_at"))


def pages(inv):
    """The pages the invocation set, in report order."""
    return [p for p in stats.PAGE_ORDER if p in inv.data.get("pages", {})]


class Page:
    """One page's result. On mobile, `after` is the latest Measurement of what both themes
    now hold, as the stop rule reads it, and `after_from` names the Round that took it.
    Desktop is the baseline against the final Measurement on the Working theme."""

    def __init__(self, inv, page):
        self.page = page
        self.desktop = (figures(inv, stats.BASELINE, page, "desktop", "control"),
                        figures(inv, stats.FINAL, page, "desktop", "working"))
        self.before = figures(inv, stats.BASELINE, page, "mobile", "control")
        self.ceiling = planning.ceiling(inv, page)
        self.target = planning.target(inv, page)
        self.after, self.after_from = None, None
        if rounds_ran(inv):
            _, source = rounds.kept_state(inv)[page]
            self.after_from = None if source == "baseline" else int(source.split("-")[1])
            self.after = self.before if self.after_from is None else \
                figures(inv, source, page, "mobile", side(inv, self.after_from))

    @property
    def state(self):
        """reached, missed (the Rounds ran short of the target), short (no Round ran),
        no-target (no Ceiling), or not-measured (no baseline)."""
        if self.before is None:
            return "not-measured"
        if self.target is None:
            return "no-target"
        if self.after is None:
            return "reached" if self.before[0] >= self.target else "short"
        return "reached" if self.after[0] >= self.target else "missed"

    @property
    def short_by(self):
        return self.target - self.after[0] if self.state == "missed" else None


def side(inv, n):
    """The theme whose Samples measured the kept state in Round n: the Working theme
    when it was kept, the Control theme when it was removed."""
    found = next(r for r in inv.data.get("rounds", []) if r["n"] == n)
    return "working" if found["state"] == "kept" else "control"


def results(inv):
    return [Page(inv, page) for page in pages(inv)]


# -- why a target was missed, and what to try next ---------------------------------

STATE_WORDS ={"reached": "reached its target", "short": "was never tried: no Round ran",
               "no-target": "has no target", "not-measured": "was not measured"}


def read_missed(path):
    try:
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, ValueError) as e:
        raise Refused("bad-missed", "%s cannot be read as JSON: %s" % (path, e))
    if not isinstance(entries, dict) or not entries:
        raise Refused("bad-missed", "%s holds no pages: give a JSON object keyed by page" % path)
    return entries


def record_missed(inv, entries):
    """Keep the reason and the proposed next plan written for each missed target.

    Only a page that missed its target is explained, and each needs a reason and
    at least one next item stating its change, cause and expected effect.
    Recording again replaces every explanation.
    """
    found = {r.page: r for r in results(inv)}
    kept = {}
    for page, entry in entries.items():
        if page not in found:
            raise Refused("bad-missed", "%s is not one of this invocation's pages (%s)"
                          % (page, ", ".join(found)))
        result = found[page]
        if result.state != "missed":
            raise Refused("bad-missed", "%s %s, so it has no missed target to explain"
                          % (page, STATE_WORDS[result.state]))
        if not isinstance(entry, dict) or not isinstance(entry.get("reason"), str) \
                or not entry["reason"].strip():
            raise Refused("bad-missed", "%s states no reason" % page,
                          "Say why the page stayed short of its target.")
        items = entry.get("next")
        if not isinstance(items, list) or not items:
            raise Refused("bad-missed", "%s proposes no next plan" % page,
                          "Give at least one next item, as plan items are given.")
        for n, item in enumerate(items, 1):
            field = planning.unstated(item) if isinstance(item, dict) else planning.ITEM_FIELDS[0]
            if field:
                raise Refused("bad-missed", "%s proposes next item %d with no %s" % (page, n, field),
                              "Each next item states its change, its cause and its expected "
                              "effect.")
        kept[page] = {"reason": entry["reason"].strip(),
                      "next": [{f: item[f].strip() for f in planning.ITEM_FIELDS} for item in items]}
    report = inv.data.setdefault("report", {})
    report["missed"] = kept
    report["missed_at"] = clock.now()
    inv.log("report", "missed targets explained: %s" % ", ".join(kept))
    inv.save()


def explanation(inv, page):
    """The reason and next plan recorded for the page's missed target, or None."""
    return ((inv.data.get("report") or {}).get("missed") or {}).get(page)


# -- the Rounds, in words -------------------------------------------------------------

def why_removed(reasons):
    """A removed Round's reasons, as words."""
    decisive = "%d of %d" % (rounds.DECISIVE, rounds.PAIRS_PER_PAGE)
    words = {
        "no-win": "it won %s pairs on none of its pages" % decisive,
        "smoke-regression": "the smoke check found something broken that works on the Control "
                            "theme",
        "new-error": "a console or Liquid error appeared that the Control theme does not have",
        "push-errors": "the store refused the change",
        "not-pushed": "the change never reached the Working theme",
        "unmeasured": "its pairs could not all be taken",
        "unchecked": "its smoke check could not run",
        "changed-since-push": "the files changed after the change was measured",
        "commit-refused": "the repo's commit hook refused the commit",
    }
    out = []
    for reason in reasons:
        kind, _, page = reason.partition(":")
        if kind == "loss":
            out.append("it lost %d or more of %d pairs on %s" % (rounds.DECISIVE,
                                                                 rounds.PAIRS_PER_PAGE, page))
        elif kind == "accessibility":
            out.append("the accessibility score fell on %s" % page)
        else:
            out.append(words.get(reason, reason))
    return ", and ".join(out)
