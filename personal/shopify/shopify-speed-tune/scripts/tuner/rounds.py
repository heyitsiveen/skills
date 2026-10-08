"""Rounds: one plan item applied to the Working theme, measured, then kept or removed.

A Round lives in the ledger's `rounds` list. It opens on the invocation's
branch with a clean tree, recording its base commit and the untracked files
already present, so its change is exactly what was edited since. Every
operation that acts on the open Round first checks the repo is still where the
Round left it.
"""

from tuner import change, clock, planning, repo, smoke, stats
from tuner.output import Refused

PAIRS_PER_PAGE = 5
# A change is kept only with this many wins of five pairs on a target page, and
# removed when any page has this many losses.
DECISIVE = 4


def label(n):
    return "round-%d" % n


def status_line(rnd):
    """One line per Round for `status`: its state, item, and any template JSON it changed."""
    if rnd["state"] == "open":
        stage = "failed" if rnd.get("failed") else "pushed" if rnd.get("change") else "applying"
        head = "%d open item=%s %s" % (rnd["n"], rnd["item"], stage)
    elif rnd["state"] == "kept":
        head = "%d kept item=%s commit=%s" % (rnd["n"], rnd["item"], rnd["commit"][:12])
    else:
        head = "%d removed item=%s" % (rnd["n"], rnd["item"])
        if (rnd.get("verdict") or {}).get("measured") is False:
            head += " not-measured"
    templates = (rnd.get("change") or {}).get("template_json") or []
    return head + (" template-json=%s" % ",".join(templates) if templates else "")


def current(inv):
    """The open Round, or None."""
    return next((r for r in inv.data.get("rounds", []) if r.get("state") == "open"), None)


def require_open(inv):
    found = current(inv)
    if found is None:
        raise Refused("no-round", "no Round is open", "Open one with `round`.")
    return found


def require_closed(inv, op):
    """Refuse `op` while a Round is open: the Working theme may hold a change no verdict kept."""
    found = current(inv)
    if found is not None:
        raise Refused("round-open", "Round %d is open, so the Working theme may hold a change no "
                      "verdict kept" % found["n"],
                      "End it with `verdict`, or with `verdict --remove` when it cannot be "
                      "measured, then run `%s` again." % op)


def require_branch(inv):
    """Refuse unless the repo is on the invocation's branch, at the state both themes hold:
    the last kept Round's commit, or the commit the branch started from."""
    root, branch = inv.data["repo"]["root"], inv.data["repo"]["branch"]
    here = repo.git(root, "branch", "--show-current").stdout.strip()
    if here != branch:
        raise Refused("wrong-branch", "the repo is on %s, not the invocation's branch %s"
                      % (here or "a detached HEAD", branch),
                      "Switch back with `git switch %s`; the Rounds run on that branch only." % branch)
    if current(inv) is None:
        kept = [r["commit"] for r in inv.data.get("rounds", []) if r["state"] == "kept"]
        expected = kept[-1] if kept else inv.data["repo"]["start_commit"]
        if repo.head(root) != expected:
            raise Refused("head-moved", "%s is at %s, but both themes hold %s"
                          % (branch, repo.head(root)[:12], expected[:12]),
                          "Only a kept Round commits on this branch. Put it back with "
                          "`git reset --soft %s` (the extra commits' changes stay in the tree) "
                          "and show the developer." % expected)


def require_place(inv, rnd):
    """Refuse unless the repo is on the invocation's branch at the Round's base commit."""
    require_branch(inv)
    root = inv.data["repo"]["root"]
    head = repo.head(root)
    if head != rnd["base"]:
        raise Refused("head-moved", "HEAD is %s, but Round %d started at %s"
                      % (head[:12], rnd["n"], rnd["base"][:12]),
                      "A Round's change stays uncommitted until its verdict, which commits it. "
                      "Run `git reset --soft %s` to put the change back in the working tree, "
                      "then run this again." % rnd["base"])


def require_measurable(inv, rnd):
    """Refuse unless the Working theme holds the Round's change, exactly as the tree has it."""
    if rnd.get("failed"):
        raise Refused("round-failed", "Round %d failed its push: %s" % (rnd["n"], rnd["failed"]),
                      "Run `verdict`: it removes the change and restores the Working theme.")
    if not rnd.get("change"):
        raise Refused("round-not-pushed", "Round %d's change has not reached the Working theme"
                      % rnd["n"], "Push it with `push` first.")
    require_place(inv, rnd)
    root = inv.data["repo"]["root"]
    entries = change.compute(root, rnd["base"], set(rnd["untracked"]))
    if change.fingerprint(root, entries) != rnd["change"]["fingerprint"]:
        raise Refused("changed-since-push", "the working tree no longer holds what Round %d "
                      "pushed to the Working theme" % rnd["n"],
                      "Before the smoke check, `push` again. After it, the change "
                      "measured is not the one in the tree, and `verdict` removes the Round.")


def require_smoke_passed(inv, rnd):
    """Refuse pairs until the Round's smoke check passed. It runs first: it warms the
    store's cache with the changed files, and a change it finds broken is removed
    without fifteen minutes of pairs."""
    record = smoke_record(inv, rnd)
    if record is None:
        raise Refused("round-unchecked", "Round %d has no smoke check yet" % rnd["n"],
                      "Run `smoke` first; the pairs follow a passing one.")
    if not smoke.judge(record["pages"]).passed:
        raise Refused("smoke-failed", "Round %d's smoke check failed, so its pairs would decide "
                      "nothing" % rnd["n"], "Run `verdict`: it removes the Round unmeasured.")


def measured_yet(inv, rnd):
    """True once any pair Sample or smoke check of the Round was taken."""
    return any(s.get("round") == rnd["n"] for s in inv.data.get("samples", [])) or \
        any(r["label"] == label(rnd["n"]) for r in inv.data.get("smoke", []))


def pair_samples(inv, rnd, page):
    """The Round's counted Samples on `page`, by pair number: {k: {theme: sample}}."""
    found = {}
    for s in inv.data.get("samples", []):
        if s.get("round") == rnd["n"] and s["page"] == page and not s.get("discarded"):
            found.setdefault(s["pair"], {})[s["theme"]] = s
    return found


def pairs(inv, rnd, page):
    """[(k, control Sample, working Sample)] of the page's complete pairs, in order."""
    found = pair_samples(inv, rnd, page)
    return [(k, found[k]["control"], found[k]["working"]) for k in sorted(found)
            if "control" in found[k] and "working" in found[k]][:PAIRS_PER_PAGE]


def discard_unpaired(inv, rnd, page):
    """Set aside each counted Sample whose pair never completed, so the pair is retaken
    back to back."""
    for k, themes in pair_samples(inv, rnd, page).items():
        if len(themes) == 1:
            for s in themes.values():
                s["discarded"] = "unpaired"


def outcome(control, working):
    c, w = control["metrics"]["performance"], working["metrics"]["performance"]
    return "win" if w > c else "loss" if w < c else "tie"


def pair_line(rnd, page, k, control, working):
    return "%d %s %d control=%d working=%d %s" % (
        rnd["n"], page, k, control["metrics"]["performance"], working["metrics"]["performance"],
        outcome(control, working))


def page_summary(inv, rnd, page):
    """{wins, losses, ties, performance: [control, working], accessibility: [...]}: medians."""
    found = pairs(inv, rnd, page)
    outcomes = [outcome(c, w) for _, c, w in found]
    out = {"wins": outcomes.count("win"), "losses": outcomes.count("loss"),
           "ties": outcomes.count("tie"), "pairs": len(found)}
    sides = ([c for _, c, _ in found], [w for _, _, w in found])
    for metric in ("performance", "accessibility"):
        out[metric] = [int(stats.median([s["metrics"][metric] for s in side])) for side in sides] \
            if found else None
    return out


def summary_line(rnd, page, summary):
    return "%d %s wins=%d losses=%d ties=%d performance=%d->%d accessibility=%d->%d" % (
        rnd["n"], page, summary["wins"], summary["losses"], summary["ties"],
        summary["performance"][0], summary["performance"][1],
        summary["accessibility"][0], summary["accessibility"][1])


def item_of(inv, rnd):
    return next(i for i in inv.data["plan"]["items"] if i["id"] == rnd["item"])


def smoke_record(inv, rnd):
    return next((r for r in inv.data.get("smoke", []) if r["label"] == label(rnd["n"])), None)


def complete(inv, rnd):
    return all(len(pairs(inv, rnd, page)) == PAIRS_PER_PAGE for page in stats.PAGE_ORDER)


def decide(inv, rnd):
    """The verdict on a measured and smoke-checked Round.

    Keep only when the change wins at least 4 of 5 pairs on one of its target
    pages (a tie is no win), no page loses 4 or more, no page's median
    accessibility score is lower on the Working theme, and the smoke check
    finds nothing the Working theme does worse: no check regression, no lost
    app block, no new console or Liquid error.
    """
    pages = {page: page_summary(inv, rnd, page) for page in stats.PAGE_ORDER}
    won = [p for p in item_of(inv, rnd)["pages"] if pages[p]["wins"] >= DECISIVE]
    reasons = [] if won else ["no-win"]
    reasons += ["loss:%s" % p for p in stats.PAGE_ORDER if pages[p]["losses"] >= DECISIVE]
    reasons += ["accessibility:%s" % p for p in stats.PAGE_ORDER
                if pages[p]["accessibility"][1] < pages[p]["accessibility"][0]]
    reasons += smoke_reasons(smoke.judge(smoke_record(inv, rnd)["pages"]))
    return {"decision": "remove" if reasons else "keep", "reasons": reasons, "won": won,
            "pages": pages, "measured": True}


def smoke_reasons(judgement):
    """The verdict's reasons from a smoke judgement: what the Working theme does worse."""
    reasons = []
    if judgement.count("regression") or judgement.count("missing app block"):
        reasons.append("smoke-regression")
    if judgement.count("new error"):
        reasons.append("new-error")
    return reasons


def kept_side(rnd):
    """The theme whose Samples in closed Round `rnd` measured the state both themes then
    hold: the Working theme when the Round was kept, the Control theme when removed."""
    return "working" if rnd["state"] == "kept" else "control"


def kept_state(inv):
    """{page: (median, Round)}: each page's latest Performance median of the state both
    themes now hold, with the closed Round whose pairs measured it (kept_side says on
    which theme), or None while the baseline still does."""
    out = {page: (planning.baseline_median(inv, page), None) for page in stats.PAGE_ORDER}
    for rnd in inv.data.get("rounds", []):
        if rnd["state"] not in ("kept", "removed"):
            continue
        side = ("control", "working").index(kept_side(rnd))
        for page in stats.PAGE_ORDER:
            if len(pairs(inv, rnd, page)) == PAIRS_PER_PAGE:
                out[page] = (page_summary(inv, rnd, page)["performance"][side], rnd)
    return out


def stop_check(inv):
    """([(tag, text)], reason): a TARGET line per page, then STOP with its reason
    (targets-reached, plan-exhausted) or NEXT with the next unused plan item."""
    lines, reached = [], True
    for page, (median, measured_in) in kept_state(inv).items():
        target = planning.target(inv, page)
        reached = reached and median >= target
        lines.append(("TARGET", "%s kept=%d target=%d %s from=%s" % (
            page, median, target, "reached" if median >= target else "short",
            "baseline" if measured_in is None else label(measured_in["n"]))))
    left = planning.unused(inv)
    reason = "targets-reached" if reached else None if left else "plan-exhausted"
    if reason:
        lines.append(("STOP", reason))
    else:
        lines.append(("NEXT", "item=%s unused=%d" % (left[0]["id"], len(left))))
    return lines, reason


def record_stop(inv, reason):
    if not inv.data.get("stopped"):
        inv.data["stopped"] = {"reason": reason, "at": clock.now()}
        inv.log("stop", "the Rounds stopped: %s" % reason)
        inv.save()


def removal(*reasons):
    """A removal the pairs did not decide: the Round is not measured."""
    return {"decision": "remove", "reasons": list(reasons), "won": [], "pages": None,
            "measured": False}


def verdict_line(rnd):
    found = rnd["verdict"]
    if found["decision"] == "keep":
        return "%d keep item=%s won=%s" % (rnd["n"], rnd["item"], ",".join(found["won"]))
    return "%d remove item=%s reasons=%s" % (rnd["n"], rnd["item"], ",".join(found["reasons"]))


def commit_message(inv, rnd):
    """(subject, body): a Conventional Commit in the client repos' own style, e.g.
    `perf(home): load the hero image eagerly`, with the Round's evidence below."""
    item = item_of(inv, rnd)
    scope = item["pages"][0] if len(item["pages"]) == 1 else "theme"
    text = item["change"].strip().rstrip(".")
    if text[1:2].islower():
        text = text[0].lower() + text[1:]
    subject = "perf(%s): %s" % (scope, text)
    if len(subject) > 72:
        subject = subject[:69].rsplit(" ", 1)[0] + "..."
    pages = rnd["verdict"]["pages"]
    body = ["Plan item %s, Round %d of invocation %s." % (item["id"], rnd["n"], inv.id)]
    if subject.endswith("..."):
        body.append("Change: %s." % item["change"].strip().rstrip("."))
    body += ["Cause: %s." % item["cause"].strip().rstrip("."), ""]
    for page in stats.PAGE_ORDER:
        found = pages[page]
        body.append("- %s: %d of %d pairs won, %d lost; median Performance %d -> %d"
                    % (page, found["wins"], found["pairs"], found["losses"],
                       found["performance"][0], found["performance"][1]))
    return subject, "\n".join(body)
