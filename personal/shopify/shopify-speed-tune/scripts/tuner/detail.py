"""The report's detail log: the record behind the part for the team.

Every Measurement with each metric's median and range, every Round with its
change, pushes, pairs, smoke check, verdict, and its commit or its revert,
every smoke check, and the Lighthouse and Chrome that took every Sample, all
read from the ledger, so any decision can be audited afterwards.
"""

from tuner import outcome, rounds, smoke, stats, tools
from tuner.text import COLUMNS, PAGE_NAMES, cell, theme_name, when

STATUS = {"M": "modified", "A": "added", "D": "deleted"}


def render(inv):
    lines = ["## Detail log", "",
             "The record behind the part above, read from the invocation's ledger, "
             "`ledger.json`, beside this report. Each Sample's Lighthouse report is in "
             "`samples/`, named by its id.", ""]
    for part in (invocation, versions, plan, measurements, smoke_checks, all_rounds):
        lines += part(inv)
    return lines


def _counted(values):
    """`13.5.0 in all 12` or `13.5.0 in 10, 13.4.0 in 2`, for one field across Samples."""
    found = {}
    for value in values:
        found[value or "unknown"] = found.get(value or "unknown", 0) + 1
    if len(found) == 1:
        value, count = next(iter(found.items()))
        return "%s in all %d" % (value, count)
    return ", ".join("%s in %d" % item for item in sorted(found.items()))


def hook_text(record):
    if record is None:
        return "not recorded"
    detail = " ".join(str(record.get("detail") or "").split()).rstrip(".")
    return "%s%s" % (record.get("status"), ": %s" % detail if detail else "")


def invocation(inv):
    data = inv.data
    store, repo = data["store"], data["repo"]
    themes = data.get("themes", {})
    plan, psi, stopped = data.get("plan") or {}, data.get("psi"), data.get("stopped")
    lines = ["### Invocation", "",
             "- **Store.** %s (`%s`)." % (store["url"], store["myshopify"]),
             "- **Invocation.** `%s`, started %s." % (inv.id, when(data.get("created_at"))),
             "- **Requested score.** %s." % data.get("requested_score"),
             "- **Published theme at the start.** %s." % theme_name(store["published_theme"])]
    for role in ("working", "control"):
        if role in themes:
            gone = themes[role].get("deleted")
            gone = ", deleted at %s" % when(gone) if gone else ""
            lines.append("- **%s theme.** %s%s." % (role.capitalize(), theme_name(themes[role]),
                                                    gone))
    if repo.get("branch"):
        lines.append("- **Branch.** `%s`, cut from `%s` at `%s`." % (
            repo["branch"], repo.get("start_branch"), (repo.get("start_commit") or "?")[:12]))
    lines.append("- **Commit hook.** %s." % hook_text(outcome.hook(data)))
    if plan:
        approved = "approved at %s" % when(plan["approved_at"]) if plan.get("approved_at") \
            else "not approved"
        lines.append("- **Plan.** %d items, %s." % (len(plan["items"]), approved))
    psi = "recorded at %s" % when(psi["recorded_at"]) if psi else "not recorded"
    stopped = "%s at %s" % (stopped["reason"], when(stopped["at"])) if stopped \
        else "the Rounds did not stop on their own"
    lines += ["- **PageSpeed scores.** %s." % psi, "- **Stop.** %s." % stopped]
    return lines + [""]


def versions(inv):
    data = inv.data
    pinned = data.get("tools") or {}
    samples = data.get("samples", [])
    lines = ["### Tools", "",
             "- **Pinned for the invocation.** Lighthouse %s on Chrome for Testing %s; "
             "puppeteer-core %s drives the smoke checker." % (
                 pinned.get("lighthouse", tools.LIGHTHOUSE),
                 (pinned.get("chrome") or {}).get("build", tools.CHROME_BUILD),
                 pinned.get("puppeteer", tools.PUPPETEER))]
    if samples:
        lines += [
            "- **Read back from the %d Samples' own reports.** Lighthouse %s. Chrome %s: its "
            "user agent names the major version only. axe-core %s." % (
                len(samples), _counted(s.get("lighthouse") for s in samples),
                _counted(s.get("chrome") for s in samples),
                _counted(s.get("axe") for s in samples))]
    return lines + [""]


def plan(inv):
    found = inv.data.get("plan")
    if not found:
        return []
    used = {r["item"]: r for r in inv.data.get("rounds", [])}
    lines = ["### Plan", ""]
    for item in found["items"]:
        rnd = used.get(item["id"])
        known = "; fixes known defect%s %s" % ("s" if len(item["defects"]) > 1 else "",
                                              ", ".join(item["defects"])) if item["defects"] else ""
        lines.append("- **%s** (%s%s): %s. Cause: %s. Expected effect: %s. %s." % (
            item["id"], ", ".join(item["pages"]), known, item["change"].rstrip("."),
            item["cause"].rstrip("."), item["effect"].rstrip("."),
            "Round %d, %s" % (rnd["n"], rnd["state"]) if rnd else "Not used"))
    return lines + [""]


def measurements(inv):
    lines = ["### Measurements", "",
             "Every Measurement: five Samples of one page, device and theme, each metric's median "
             "with its range in brackets.", "",
             "| Measurement | Page | Device | Theme | Samples | %s |" % " | ".join(COLUMNS),
             "|---|---|---|---|---|%s" % ("---|" * len(COLUMNS))]
    for measurement, members in stats.measurements(inv.data):
        head = "| %s | %s | %s | %s |" % (measurement.label,
                                          PAGE_NAMES.get(measurement.page, measurement.page),
                                          measurement.device, measurement.theme.capitalize())
        if len(members) < stats.SAMPLES_PER_MEASUREMENT:
            lines.append("%s %d of %d | %s |" % (head, len(members), stats.SAMPLES_PER_MEASUREMENT,
                                                 " | ".join("–" for _ in COLUMNS)))
            continue
        figures = stats.summary(members)
        lines.append("%s %d | %s |" % (head, len(members), " | ".join(
            cell(m, *figures[m]) for m in stats.METRICS)))
    rejected = [e for e in inv.data.get("events", [])
                if e.get("op") == "sample" and e.get("text", "").startswith("rejected ")]
    if rejected:
        lines += ["", "Samples rejected before they were recorded, so counted nowhere:", ""]
        lines += ["- %s: %s." % (when(e["at"]), e["text"][len("rejected "):]) for e in rejected]
    return lines + [""]


def smoke_checks(inv):
    records = inv.data.get("smoke", [])
    if not records:
        return []
    lines = ["### Smoke checks", ""]
    for record in records:
        judgement = smoke.judge(record["pages"])
        lines.append("- **%s**, %s, from the %s: %s." % (
            record["label"], when(record.get("taken_at")), record.get("source"),
            smoke.result_line(record["label"], judgement)))
        lines += ["  - %s" % line for line in judgement.lines(record["label"])]
        lines += ["  - %s" % smoke.page_line(record["label"], page, role, record["pages"][page][role])
                  for page in smoke.PAGES for role in smoke.ROLES]
    return lines + [""]


def all_rounds(inv):
    found = inv.data.get("rounds", [])
    if not found:
        return []
    lines = ["### Rounds", ""]
    for rnd in found:
        lines += one_round(inv, rnd)
    return lines


def push_text(attempt):
    result = attempt.get("result")
    if result == "errors":
        detail = "; ".join("%s: %s" % (path, " ".join(messages))
                           for path, messages in sorted((attempt.get("errors") or {}).items()))
        result = "refused with errors (%s)" % (detail or attempt.get("warning"))
    elif result == "failed":
        result = "did not finish (%s)" % attempt.get("detail")
    return "%s: the %s theme #%s, %d path%s, %s" % (
        when(attempt.get("at")), str(attempt.get("theme")).capitalize(), attempt.get("id"),
        len(attempt["paths"]),
        "" if len(attempt["paths"]) == 1 else "s", result)


def verdict_text(rnd):
    found = rnd.get("verdict") or {}
    if found.get("decision") == "keep":
        pages = found.get("pages") or {}
        return "keep: won %s" % ", ".join("%d of %d pairs on %s" % (
            pages[p]["wins"], pages[p]["pairs"], p) for p in found["won"])
    if found.get("decision") == "remove":
        return "remove: %s" % outcome.why_removed(found["reasons"])
    return "none yet"


def one_round(inv, rnd):
    item = rounds.item_of(inv, rnd)
    themes = inv.data["themes"]
    lines = ["#### Round %d: %s, %s" % (rnd["n"], item["id"], rnd["state"]), "",
             "- **Item.** %s (%s). Cause: %s. Expected effect: %s." % (
                 item["change"].rstrip("."), ", ".join(item["pages"]), item["cause"].rstrip("."),
                 item["effect"].rstrip(".")),
             "- **Opened** %s at `%s`%s." % (when(rnd.get("opened_at")), rnd["base"][:12],
                                            "; **closed** %s" % when(rnd["closed_at"])
                                            if rnd.get("closed_at") else "")]
    entries = (rnd.get("change") or {}).get("entries")
    if entries:
        flagged = set((rnd.get("change") or {}).get("template_json") or [])
        lines.append("- **Change.** %s." % ", ".join(
            "%s `%s`%s" % (STATUS.get(status, status), path,
                           " (template JSON)" if path in flagged else "")
            for status, path in entries))
    pushes = rnd.get("pushes") or []
    lines.append("- **Pushes.** %s." % ("; ".join(push_text(a) for a in pushes) if pushes
                                        else "none: the change never reached the Working theme"))
    taken = any(rounds.pairs(inv, rnd, page) for page in stats.PAGE_ORDER)
    if outcome.measured(inv, rnd):
        lines.append("- **Pairs.** Each a Control theme Sample, then a Working theme Sample, back "
                     "to back, below.")
    else:
        lines.append("- **Pairs.** Not measured%s" % (": the pairs below did not decide this "
                                                      "Round." if taken else "."))
    record = rounds.smoke_record(inv, rnd)
    if record is not None:
        judgement = smoke.judge(record["pages"])
        lines.append("- **Smoke check.** %s" % smoke.result_line(record["label"], judgement))
        lines += ["  - %s" % line for line in judgement.lines(record["label"])]
    lines.append("- **Verdict.** %s." % verdict_text(rnd))
    for line in rnd.get("commit_refused") or []:
        lines.append("  - the commit hook said: %s" % line)
    if rnd["state"] == "kept":
        subject = rounds.commit_message(inv, rnd)[0]
        lines.append("- **Commit.** `%s` %s" % (rnd["commit"][:12], subject))
        if rnd.get("reformatted"):
            lines.append("  - the commit hook rewrote %s; both themes got the committed version"
                         % ", ".join("`%s`" % p for p in rnd["reformatted"]))
        if rnd.get("control_pushed"):
            lines.append("- **Control theme.** Brought up to date at %s." % when(rnd["control_pushed"]))
    elif rnd["state"] == "removed" and rnd.get("restored"):
        back = ", and the Working theme #%s was pushed back to it at %s" % (
            themes["working"]["id"], when(rnd["working_restored"])) \
            if rnd.get("working_restored") else "; nothing had reached the Working theme"
        lines.append("- **Revert.** The working tree was put back at %s%s." % (
            when(rnd["restored"]), back))
    lines.append("")
    if taken:
        lines += pair_tables(inv, rnd)
    return lines


def pair_tables(inv, rnd):
    lines = ["| Page | Pair | Control | Working | Outcome | Samples |",
             "|---|---|---|---|---|---|"]
    for page in stats.PAGE_ORDER:
        for k, control, working in rounds.pairs(inv, rnd, page):
            lines.append("| %s | %d | %d | %d | %s | %s, %s |" % (
                page, k, control["metrics"]["performance"], working["metrics"]["performance"],
                rounds.outcome(control, working), control["id"], working["id"]))
    lines += ["", "| Page | Wins | Losses | Ties | Performance, Control → Working | "
                  "Accessibility, Control → Working |", "|---|---|---|---|---|---|"]
    for page in stats.PAGE_ORDER:
        if len(rounds.pairs(inv, rnd, page)) == rounds.PAIRS_PER_PAGE:
            found = rounds.page_summary(inv, rnd, page)
            lines.append("| %s | %d | %d | %d | %d → %d | %d → %d |" % (
                page, found["wins"], found["losses"], found["ties"],
                found["performance"][0], found["performance"][1],
                found["accessibility"][0], found["accessibility"][1]))
        else:
            lines.append("| %s | not measured | | | | |" % page)
    return lines + [""]
