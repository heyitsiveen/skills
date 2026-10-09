"""report: write the invocation's report into its folder, generated from the ledger.

The report has two parts. The part for the team says what changed; each page's
Performance score before and after, against its target and its Ceiling, with
desktop at the start and the end; the developer's PageSpeed Insights mobile
Performance scores beside the baseline; what every app and tag costs; the template JSON a kept Round changed;
how this store goes live and goes back; and, for each missed target, why and
what to try next. The detail log is the record behind it.

A missed target's reason and next plan are the one part the program cannot
know: `--missed FILE` records them, written for each page that missed, and the
report carries them. Until then each such page prints `REPORT missed <page>
unexplained`.

Desktop is measured again at the end of every invocation, whatever ended it. A
final desktop Measurement not taken is flagged in the report, and while the
invocation is open a NOTE names the `final` call that takes it.

The store's setup is read from the repo, and its published theme from the
theme library, at the time of the report: how to go live depends on both.
"""

from tuner import clock, detail, findings, golive, ledger, outcome, planning, rounds, stats
from tuner.output import note, say
from tuner.text import page_name, psi_table, score, theme_name, when

ORDER = 85


def register(sub):
    p = sub.add_parser("report", help="write the report: a part for the team and a detail log")
    p.add_argument("--missed", metavar="FILE",
                   help="record each missed target's reason and proposed next plan from a JSON "
                        "file, then write the report")
    p.add_argument("--invocation", help="a finished invocation of this repo, by id")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.find(args.invocation)
    rounds.require_closed(inv, "report")
    if args.missed:
        outcome.record_missed(inv, outcome.read_missed(args.missed))
    results = outcome.results(inv)
    live, unread = golive.live_theme(inv)
    setup = golive.detect(inv.root, live["name"])
    path = inv.file("report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(inv, results, setup, live))
    inv.data.setdefault("report", {})["written_at"] = clock.now()
    inv.log("report", "report written")
    inv.save()
    if unread:
        note(unread)
    if golive.changed(inv, live):
        recorded = inv.data["store"]["published_theme"]
        say("WARN", "live-theme-changed: the published theme is %s (#%s) now, not %s (#%s), the "
                    "theme the Working theme was copied from" % (live["name"], live["id"],
                                                                 recorded["name"], recorded["id"]))
    for result in results:
        say("REPORT", page_line(result))
    if inv.data.get("state") == "open":
        for result in results:
            if result.desktop[1] is None:
                note("the %s page's final desktop Measurement holds %d of %d Samples: take it "
                     "with `final --page %s`, then write the report again" % (
                         result.page, final_held(inv, result.page), stats.SAMPLES_PER_MEASUREMENT,
                         result.page))
    say("REPORT", "setup", setup.kind, "branch=%s" % setup.branch if setup.branch else "")
    missed = [r.page for r in results if r.state == "missed"]
    for page in missed:
        say("REPORT", "missed", page,
            "unexplained" if outcome.explanation(inv, page) is None else "explained")
    if any(outcome.explanation(inv, page) is None for page in missed):
        note("each missed target needs its reason and a proposed next plan: write them to a "
             "JSON file and run `report --missed <file>`")
    say("REPORT", "file", path)
    return 0


def final_held(inv, page):
    return len(stats.members(inv.data["samples"],
                             stats.Measurement.of(inv, stats.FINAL, page, "desktop", "working")))


def _number(figures):
    return "-" if figures is None else "%d" % figures[0]


def page_line(result):
    target = "-" if result.target is None else "%d" % result.target
    return "page %s before=%s after=%s target=%s %s%s" % (
        result.page, _number(result.before), _number(result.after), target, result.state,
        " by=%d" % result.short_by if result.state == "missed" else "")


# -- the report ------------------------------------------------------------------

def render(inv, results, setup, live):
    data = inv.data
    table = measured_costs(inv)
    kept = any(r["state"] == "kept" for r in data.get("rounds", []))
    pinned = data.get("tools") or {}
    lines = ["# Speed report: %s" % inv.store_url, "",
             "Invocation `%s`, started %s, measured with Lighthouse %s on Chrome for Testing %s. "
             "Requested Performance score: %s." % (
                 inv.id, when(data.get("created_at")), pinned.get("lighthouse", "?"),
                 (pinned.get("chrome") or {}).get("build", "?"), data.get("requested_score")),
             "", "**Outcome.** %s" % outcome_words(inv, results), "", "## For the team", ""]
    lines += what_changed(inv)
    lines += performance(inv, results)
    lines += pagespeed(inv)
    lines += apps_and_tags(inv, table)
    lines += template_json(inv)
    lines += golive.section(inv, setup, live, kept)
    lines += missed_targets(inv, [r for r in results if r.state == "missed"], table)
    lines += detail.render(inv)
    return "\n".join(lines).rstrip() + "\n"


def no_round(plan):
    return "No Round ran: %s" % ("the plan was not approved." if plan else
                                 "the invocation stopped before its plan.")


def outcome_words(inv, results):
    plan = inv.data.get("plan") or {}
    if not plan.get("approved_at"):
        return no_round(plan)
    reason = (inv.data.get("stopped") or {}).get("reason")
    if reason == "targets-reached":
        used = len(plan["items"]) - len(planning.unused(inv))
        return "Every page reached its target, so the Rounds stopped after %d of the plan's %d " \
               "items." % (used, len(plan["items"]))
    reached = "%d of %d pages at their targets" % (
        sum(1 for r in results if r.state == "reached"), len(results))
    if reason == "plan-exhausted":
        return "The plan was used up with %s." % reached
    return "The Rounds were ended before the plan was used up, with %s." % reached


def item_head(item):
    return "**%s. %s.**" % (item["id"], item["change"].strip().rstrip("."))


def item_text(item):
    return "%s (%s)" % (item["id"], item["change"].strip().rstrip("."))


def kept_line(rnd, item):
    pages = rnd["verdict"]["pages"]
    parts = []
    for page in stats.PAGE_ORDER:
        found = pages[page]
        figures = (found["wins"], found["pairs"]) + tuple(found["performance"])
        parts.append(("%s won %d of %d pairs (median %d → %d)" if not parts
                      else "%s %d of %d (%d → %d)") % ((page,) + figures))
    return "- %s Kept in Round %d, commit `%s`: %s." % (item_head(item), rnd["n"],
                                                      rnd["commit"][:12], ", ".join(parts))


def what_changed(inv):
    data = inv.data
    plan = data.get("plan") or {}
    lines = ["### What changed", ""]
    if not plan.get("approved_at"):
        return lines + [no_round(plan), ""]
    items = {item["id"]: item for item in plan["items"]}
    done = [r for r in data.get("rounds", []) if r["state"] in ("kept", "removed")]
    kept = [r for r in done if r["state"] == "kept"]
    working = data["themes"].get("working", {})
    intro = "%d of the plan's %d items %s kept." % (len(kept), len(items),
                                                    "was" if len(kept) == 1 else "were")
    if kept:
        intro += " Each kept item is one commit on the branch `%s`, and the Working theme %s " \
                 "holds them all." % (data["repo"]["branch"], theme_name(working))
    else:
        intro += " The Working theme %s is still a copy of the published theme." \
                 % theme_name(working)
    lines += [intro, ""]
    lines += [kept_line(rnd, items[rnd["item"]]) for rnd in kept]
    lines += ["- %s Removed in Round %d%s, because %s." % (
        item_head(items[rnd["item"]]), rnd["n"],
        "" if rnd["verdict"]["measured"] else " without being measured",
        outcome.why_removed(rnd["verdict"]["reasons"]))
        for rnd in done if rnd["state"] == "removed"]
    reached = (data.get("stopped") or {}).get("reason") == "targets-reached"
    lines += ["- %s Not tried: %s" % (item_head(item), "every page reached its target first."
                                      if reached else "the Rounds were ended before it.")
              for item in planning.unused(inv)]
    lines += css_check(kept)
    hook = data["hook"]
    if kept and hook["status"] == "bypass-approved":
        # A ledger an earlier release wrote keeps the hook's output in its detail only.
        said = (hook["output"] or ["no output"]) if "output" in hook \
            else [str(hook.get("detail") or "").strip()]
        lines += ["", "The kept Rounds were committed with `--no-verify`: the repo's pre-commit "
                      "hook already failed before this invocation, and the developer approved the "
                      "bypass for it, so the hook checked none of these commits. The end of what "
                      "it said before the invocation:", "", "```"] + said + ["```"]
    return lines + [""]


def css_check(kept):
    """A look by eye before going live, for the kept Rounds whose change touched CSS: no
    check in a Round looks at how a page is styled."""
    found = [(rnd["n"], (rnd.get("change") or {}).get("css")) for rnd in kept]
    found = [(n, paths) for n, paths in found if paths]
    if not found:
        return []
    rounds_said = "; ".join("Round %d %sin %s" % (n, "" if i else "changed CSS ",
                                                  listed(["`%s`" % p for p in paths]))
                            for i, (n, paths) in enumerate(found))
    return ["", "**Look before going live.** %s. Neither the smoke check nor the pairs look at "
                "how a page is styled, so compare the Working theme's pages with the published "
                "theme's by eye before publishing it." % rounds_said]


RESULT = {"reached": "reached", "short": "no Round ran", "no-target": "no target: no Ceiling",
          "not-measured": "not measured"}


def performance(inv, results):
    lines = ["### Performance by page", "",
             "| Page | Before | After | Target | Ceiling (estimate) | Result |",
             "|---|---|---|---|---|---|"]
    for r in results:
        after = score(r.after)
        if r.after is not None:
            after += ", Round %d" % r.after_from if r.after_from else ", the baseline"
        state = "missed by %d" % r.short_by if r.state == "missed" else RESULT[r.state]
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            page_name(r.page), score(r.before), after,
            "–" if r.target is None else r.target, score(r.ceiling), state))
    lines += [
        "",
        "Mobile Performance scores, each the median of five Samples with their range: mobile "
        "decides. **Before** is the baseline, on the Control theme. **After** is the latest "
        "Measurement of what the Working theme now holds: its own Samples in the Round that kept "
        "a change, or the Control theme's in a later Round, which held the same. **Target** is "
        "the lower of the requested %d and the page's Ceiling. The **Ceiling** is an estimate of "
        "the most theme work can reach: the page measured with the theme's scripts, fonts and "
        "images other than its LCP image blocked, while stylesheets, apps and tags stay."
        % inv.data["requested_score"],
        "",
    ]
    notes = [(page, text) for page in outcome.pages(inv)
             for text in ((inv.data.get("ceilings") or {}).get(page) or {}).get("findings", [])]
    lines += ["- %s's Ceiling: %s." % (page_name(page), text) for page, text in notes]
    lines += [""] if notes else []
    lines += ["Desktop decides nothing. It is measured at the start, on the Control theme, and at "
              "the end, on the Working theme:", "",
              "| Page | Desktop before | Desktop after |", "|---|---|---|"]
    lines += ["| %s | %s | %s |" % (page_name(r.page), score(r.desktop[0]), score(r.desktop[1]))
              for r in results]
    untaken = [page_name(r.page) for r in results if r.desktop[1] is None]
    if untaken:
        lines += ["", "The final desktop Measurement was not taken on %s, so %s Desktop after "
                      "reads –." % (listed(untaken), "its" if len(untaken) == 1 else "their")]
    return lines + [""]


def listed(names):
    """`Home`, `Home and Product`, or `Home, Collection and Product`."""
    return names[0] if len(names) == 1 else "%s and %s" % (", ".join(names[:-1]), names[-1])


def pagespeed(inv):
    lines = ["### PageSpeed beside the baseline", ""]
    kept = inv.data.get("psi")
    if not kept:
        return lines + ["The developer's PageSpeed Insights mobile Performance scores were not "
                        "recorded.", ""]
    lines += psi_table(kept, stats.PAGE_ORDER)
    lines += ["", "The developer's PageSpeed Insights mobile Performance scores, given at the plan "
                  "stop, beside this skill's baseline medians.", ""]
    _, warnings = planning.psi_lines(inv)
    lines += ["- **Warning**, %s." % w.split(" ", 1)[1] for w in warnings]
    return lines + ([""] if warnings else [])


def measured_costs(inv):
    """The app and tag cost table over every page whose baseline is complete."""
    reports = {page: [r for _, r in findings.baseline(inv, page)] for page in outcome.pages(inv)
               if outcome.figures(inv, stats.BASELINE, page, "mobile", "control") is not None}
    return findings.costs(reports) if reports else []


def apps_and_tags(inv, table):
    lines = ["### Apps and tags", ""]
    if not table:
        return lines + ["Not measured: no page has its baseline.", ""]
    return lines + findings.cost_table(table, outcome.pages(inv)) + [""]


def template_json(inv):
    """Template JSON that kept Rounds changed: page content the merchant edits too."""
    lines = ["### Template JSON", ""]
    flagged = [(path, rnd) for rnd in inv.data.get("rounds", []) if rnd["state"] == "kept"
               for path in (rnd.get("change") or {}).get("template_json") or []]
    if not flagged:
        return lines + ["No kept Round changed template JSON.", ""]
    lines += ["These files are page content the merchant edits in the theme editor too. Review "
              "each change against the published theme's copy before going live:", ""]
    lines += ["- `%s`: Round %d, %s." % (path, rnd["n"], item_text(rounds.item_of(inv, rnd)))
              for path, rnd in flagged]
    return lines + [""]


# -- missed targets ----------------------------------------------------------------

def costliest(table, page, count=3):
    here = [(cells[page][0], name) for name, cells in table if cells.get(page)]
    return [(name, ms) for ms, name in sorted(here, key=lambda c: (-c[0], c[1]))[:count]]


def round_here(inv, rnd, page):
    """What one closed Round did on one page, in a sentence."""
    head = "Round %d, %s: " % (rnd["n"], item_text(rounds.item_of(inv, rnd)))
    if rnd["state"] == "kept":
        head += "kept"
    else:
        head += "removed, because %s" % outcome.why_removed(rnd["verdict"]["reasons"])
    if not rnd["verdict"]["measured"] or len(rounds.pairs(inv, rnd, page)) < rounds.PAIRS_PER_PAGE:
        return head + "; not measured here."
    found = rounds.page_summary(inv, rnd, page)
    return head + "; won %d of %d pairs here, median %d → %d." % (
        found["wins"], found["pairs"], found["performance"][0], found["performance"][1])


def stop_words(inv):
    stopped = inv.data.get("stopped") or {}
    if stopped.get("reason") == "plan-exhausted":
        return "stopped when the plan was used up."
    if stopped.get("reason") == "targets-reached":
        return "stopped when every page reached its target."
    left = len(planning.unused(inv))
    return "were ended before the plan was used up, with %d item%s never tried." % (
        left, "" if left == 1 else "s")


def missed_facts(inv, r, table):
    requested = inv.data["requested_score"]
    if r.target < requested:
        target = "Its Ceiling, %d: an estimate of the most theme work can reach here, below the " \
                 "requested %d." % (r.target, requested)
    else:
        target = "The requested score, %d; its Ceiling, an estimate, is %d." % (requested,
                                                                              r.ceiling[0])
    tried = [round_here(inv, rnd, r.page) for rnd in inv.data.get("rounds", [])
             if rnd["state"] in ("kept", "removed")
             and r.page in rounds.item_of(inv, rnd)["pages"]]
    lines = ["- **Target.** %s" % target,
             "- **Rounds on this page.** %s" % (" ".join(tried) or "None: no plan item targeted it.")]
    top = costliest(table, r.page)
    if top:
        lines.append("- **Apps and tags here.** %s of main-thread time, each the median over the "
                     "page's baseline Samples." % ", ".join("%s %d ms" % (name, round(ms))
                                                         for name, ms in top))
    lines.append("- **The Rounds** %s" % stop_words(inv))
    return lines + [""]


def missed_targets(inv, missed, table):
    if not missed:
        return []
    lines = ["### Missed targets", ""]
    for r in missed:
        lines += ["#### %s: %d against a target of %d" % (page_name(r.page), r.after[0], r.target),
                  ""]
        lines += missed_facts(inv, r, table)
        written = outcome.explanation(inv, r.page)
        if written is None:
            lines += ["**Reason and next plan:** not written yet.", ""]
            continue
        lines += ["**Reason.** %s" % written["reason"], "", "**Proposed next plan.**", ""]
        for n, item in enumerate(written["next"], 1):
            lines += ["%d. %s" % (n, item["change"]),
                      "   - Cause: %s" % item["cause"],
                      "   - Expected effect: %s" % item["effect"]]
        lines.append("")
    return lines
