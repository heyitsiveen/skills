"""The report: a part for the team and a detail log, both generated from the ledger.

Every figure below is worked by hand from the real fixtures (see report_support).
"""

import json
import re
import unittest
from pathlib import Path

from report_support import ran
from round_support import ITEMS, approved, pushed
from support import Sandbox, report


def written(test, box, *args):
    result = box.run("report", *args)
    test.assertEqual(result.code, 0, result)
    path = Path(re.search(r"(?m)^REPORT file (\S+)$", result.out).group(1))
    return result, path.read_text()


class AReportOnEveryTargetReached(unittest.TestCase):
    def setUp(self):
        self.box = ran(self, "reached")
        self.result, self.text = written(self, self.box)

    def test_gives_each_pages_score_before_and_after_with_its_target_and_ceiling(self):
        self.assertEqual([l for l in self.result.lines("REPORT") if l.startswith("REPORT page ")], [
            "REPORT page home before=50 after=60 target=59 reached",
            "REPORT page collection before=61 after=72 target=71 reached",
            "REPORT page product before=44 after=66 target=65 reached",
        ])
        for row in ("| Home | 50 (36–56) | 60 (46–66), Round 1 | 59 | 59 (58–65) | reached |",
                    "| Collection | 61 (46–64) | 72 (57–75), Round 1 | 71 | 71 (69–82) | reached |",
                    "| Product | 44 (43–46) | 66 (65–68), Round 1 | 65 | 65 (59–68) | reached |"):
            self.assertIn(row, self.text)
        self.assertIn("| Page | Before | After | Target | Ceiling (estimate) | Result |", self.text)

    def test_gives_desktop_at_the_start_and_at_the_end(self):
        for row in ("| Page | Desktop before | Desktop after |",
                    "| Home | 88 (85–90) | 90 (89–92) |",
                    "| Collection | 88 (88–88) | 89 (89–89) |",
                    "| Product | 71 (69–72) | 75 (73–76) |"):
            self.assertIn(row, section(self.text, "### Performance by page"))

    def test_sets_the_developers_pagespeed_scores_beside_the_baseline_and_warns_on_a_gap(self):
        psi = section(self.text, "### PageSpeed beside the baseline")

        for row in ("| Page | PageSpeed | Baseline | Gap |", "| Home | 61 | 50 | +11 |",
                    "| Collection | 58 | 61 | -3 |", "| Product | 47 | 44 | +3 |"):
            self.assertIn(row, psi)
        warnings = [l for l in psi.splitlines() if l.startswith("- **Warning")]
        self.assertEqual(len(warnings), 1, psi)
        self.assertIn("home: PageSpeed's 61 is 11 points above this skill's baseline median of 50",
                      warnings[0])

    def test_gives_every_app_and_tags_cost_costliest_first(self):
        costs = section(self.text, "### Apps and tags").splitlines()

        self.assertIn("| App or tag | Home | Collection | Product |", costs)
        self.assertEqual(costs[costs.index("| App or tag | Home | Collection | Product |") + 2],
                         "| ContentSquare | 114 ms · 159 KiB | – | – |")

    def test_says_no_kept_round_changed_template_json(self):
        self.assertIn("No kept Round changed template JSON.",
                      section(self.text, "### Template JSON"))

    def test_opens_with_the_outcome(self):
        self.assertIn("**Outcome.** Every page reached its target, so the Rounds stopped after 1 of "
                      "the plan's 2 items.", self.text.split("## For the team", 1)[0])

    def test_has_no_missed_target_section(self):
        self.assertNotIn("Missed targets", self.text)
        self.assertEqual([l for l in self.result.lines("REPORT") if " missed" in l], [])

    def test_says_what_changed_with_each_kept_items_commit_and_what_was_not_tried(self):
        commit = self.box.git(self.box.repo, "rev-parse", "--short=12", "HEAD")
        changed = section(self.text, "### What changed")

        self.assertIn("1 of the plan's 2 items was kept. Each kept item is one commit on the "
                      "branch `speed-tune/", changed)
        self.assertIn("- **P2. Drop the unused slider script.** Kept in Round 1, commit `%s`: "
                      "home won 5 of 5 pairs (median 50 → 60), collection 5 of 5 (61 → 72), "
                      "product 5 of 5 (44 → 66)." % commit, changed)
        self.assertIn("- **P1. Load the hero image eagerly.** Not tried: every page reached its "
                      "target first.", changed)


class AReportOnMissedTargets(unittest.TestCase):
    """P1 was kept and P2 removed; the plan ran out short of every target. Round 2's
    Control theme Samples, which held P1, are the latest Measurement of the kept state."""

    def setUp(self):
        self.box = ran(self, "missed")
        self.result, self.text = written(self, self.box)

    def test_says_by_how_much_each_page_missed_its_target(self):
        self.assertEqual([l for l in self.result.lines("REPORT") if l.startswith("REPORT page ")], [
            "REPORT page home before=50 after=50 target=59 missed by=9",
            "REPORT page collection before=61 after=61 target=71 missed by=10",
            "REPORT page product before=44 after=44 target=65 missed by=21",
        ])
        self.assertIn("| Home | 50 (36–56) | 50 (36–56), Round 2 | 59 | 59 (58–65) | missed by 9 |",
                      self.text)

    def test_has_a_missed_target_section_for_each_page_that_missed(self):
        section = self.text.split("### Missed targets", 1)[1]

        self.assertIn("#### Home: 50 against a target of 59", section)
        self.assertIn("#### Collection: 61 against a target of 71", section)
        self.assertIn("#### Product: 44 against a target of 65", section)

    def test_opens_with_the_outcome(self):
        self.assertIn("**Outcome.** The plan was used up with 0 of 3 pages at their targets.",
                      self.text.split("## For the team", 1)[0])

    def test_says_which_items_were_removed_and_why(self):
        changed = section(self.text, "### What changed")

        self.assertIn("1 of the plan's 2 items was kept.", changed)
        self.assertRegex(changed, r"- \*\*P1\. Load the hero image eagerly\.\*\* Kept in Round 1, "
                                  r"commit `[0-9a-f]{12}`: home won 4 of 5 pairs \(median 50 → 52\), "
                                  r"collection 0 of 5 \(61 → 61\), product 0 of 5 \(44 → 44\)\.")
        self.assertIn("- **P2. Drop the unused slider script.** Removed in Round 2, because it "
                      "won 4 of 5 pairs on none of its pages.", changed)

    def test_flags_each_template_json_file_a_kept_round_changed(self):
        flagged = section(self.text, "### Template JSON")

        self.assertIn("- `templates/index.json`: Round 1, P1 (Load the hero image eagerly).",
                      flagged)
        self.assertEqual(flagged.count("- `"), 1, flagged)

    def test_states_what_the_measurements_say_about_each_missed_target(self):
        home = self.text.split("#### Home:", 1)[1].split("####", 1)[0]
        collection = self.text.split("#### Collection:", 1)[1].split("####", 1)[0]

        self.assertIn("- **Target.** Its Ceiling, 59: an estimate of the most theme work can "
                      "reach here, below the requested 80.", home)
        self.assertIn("- **Rounds on this page.** Round 1, P1 (Load the hero image eagerly): kept; "
                      "won 4 of 5 pairs here, median 50 → 52. Round 2, P2 (Drop the unused slider "
                      "script): removed, because it won 4 of 5 pairs on none of its pages; won 0 "
                      "of 5 pairs here, median 50 → 50.", home)
        self.assertIn("- **Rounds on this page.** Round 2, P2 (Drop the unused slider script): "
                      "removed, because it won 4 of 5 pairs on none of its pages; won 0 of 5 "
                      "pairs here, median 61 → 61.", collection)
        self.assertIn("- **Apps and tags here.** ContentSquare 114 ms", home)
        self.assertIn("- **The Rounds** stopped when the plan was used up.", home)

    def test_asks_for_each_missed_targets_reason_and_next_plan(self):
        self.assertEqual(missed_lines(self.result), [
            "REPORT missed home unexplained",
            "REPORT missed collection unexplained",
            "REPORT missed product unexplained",
        ])
        self.assertRegex(self.result.out, r"(?m)^NOTE .*`report --missed <file>`")


class ExplainingAMissedTarget(unittest.TestCase):
    def setUp(self):
        self.box = ran(self, "missed")

    def test_the_reason_and_next_plan_written_for_each_page_are_in_the_report(self):
        result, text = written(self, self.box, "--missed", explanations(self.box, EXPLAINED))

        self.assertEqual(missed_lines(result), [
            "REPORT missed home explained",
            "REPORT missed collection explained",
            "REPORT missed product explained",
        ])
        home = text.split("#### Home:", 1)[1].split("####", 1)[0]
        self.assertIn("**Reason.** " + EXPLAINED["home"]["reason"], home)
        self.assertIn("1. Preload the hero image after the viewport tag\n"
                      "   - Cause: the LCP image is discovered late\n"
                      "   - Expected effect: +2 to +4 on home", home)

    def test_a_page_that_reached_its_target_is_not_explained(self):
        box = ran(self, "reached")

        result = box.run("report", "--missed", explanations(box, {"home": EXPLAINED["home"]}))

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED bad-missed: home reached its target")

    def test_each_page_needs_a_reason_and_at_least_one_next_item(self):
        for broken in ({"reason": " ", "next": EXPLAINED["home"]["next"]},
                       {"reason": "apps", "next": []},
                       {"reason": "apps", "next": [{"change": "x", "cause": "y"}]}):
            result = self.box.run("report", "--missed", explanations(self.box, {"home": broken}))

            self.assertEqual(result.code, 1, result)
            self.assertRegex(result.out, r"(?m)^REFUSED bad-missed: home ")


class TheDetailLog(unittest.TestCase):
    """Round 1 kept P1 on four wins in five on home; Round 2 removed P2."""

    def setUp(self):
        self.box = ran(self, "missed")
        _, text = written(self, self.box)
        self.log = text.split("\n## Detail log\n", 1)[1]

    def test_gives_every_measurement_with_each_metrics_median_and_range(self):
        measurements = section(self.log, "### Measurements")

        self.assertIn("| baseline | Home | mobile | Control | 5 | 50 (36–56) | 10.2 s (9.4–11.0) | "
                      "672 ms (430–1,315) | 0.000 (0.000–0.000) | 3.7 s (3.6–5.2) | "
                      "3.8 s (3.7–5.6) | 94 (94–94) |", measurements)
        self.assertIn("| ceiling | Product | mobile | Control | 5 | 65 (59–68) |", measurements)
        self.assertIn("| round-1 | Home | mobile | Working | 5 | 52 (38–58) |", measurements)
        self.assertIn("| final | Home | desktop | Working | 5 | 90 (89–92) |", measurements)

    def test_gives_every_pair_of_every_round(self):
        first = section(self.log, "#### Round 1: P1, kept")

        self.assertIn("| home | 1 | 36 | 38 | win |", first)
        self.assertIn("| home | 5 | 55 | 54 | loss |", first)
        self.assertIn("| product | 3 | 46 | 46 | tie |", first)

    def test_gives_each_rounds_smoke_result_verdict_and_commit(self):
        first = section(self.log, "#### Round 1: P1, kept")
        subject = self.box.git(self.box.repo, "log", "-1", "--format=%s",
                               "--grep=Round 1 of invocation")

        self.assertIn("- **Smoke check.** round-1 result pass", first)
        self.assertIn("- **Verdict.** keep: won 4 of 5 pairs on home", first)
        self.assertRegex(first, r"- \*\*Commit\.\*\* `[0-9a-f]{12}` %s" % re.escape(subject))
        self.assertIn("`templates/index.json` (template JSON)", first)

    def test_gives_each_removed_rounds_revert(self):
        second = section(self.log, "#### Round 2: P2, removed")

        self.assertIn("- **Verdict.** remove: it won 4 of 5 pairs on none of its pages.", second)
        self.assertRegex(second, r"- \*\*Revert\.\*\* The working tree was put back at .+, and the "
                                 r"Working theme #200 was pushed back to it at .+\.")

    def test_names_the_lighthouse_and_chrome_versions(self):
        tools = section(self.log, "### Tools")

        self.assertIn("Lighthouse 13.5.0", tools)
        self.assertIn("Chrome for Testing 154.0.8037.57", tools)
        self.assertIn("HeadlessChrome/154.0.0.0", tools)


class ARoundWithNoPairs(unittest.TestCase):
    def setUp(self):
        self.box = ran(self, "first-unmeasured")
        _, self.text = written(self, self.box)

    def test_is_shown_as_not_measured_in_the_detail_log(self):
        first = section(self.text.split("\n## Detail log\n", 1)[1], "#### Round 1: P1, removed")

        self.assertIn("- **Pairs.** Not measured.", first)
        self.assertIn("- **Verdict.** remove: the change never reached the Working theme.", first)

    def test_is_told_to_the_team_as_removed_without_being_measured(self):
        self.assertIn("- **P1. Load the hero image eagerly.** Removed in Round 1 without being "
                      "measured, because the change never reached the Working theme.",
                      section(self.text, "### What changed"))


class TheCommitHookTheInvocationStartedWith(unittest.TestCase):
    """`start` records the client repo's pre-commit hook: passed, absent, or already failing
    and bypassed with the developer's approval (`--no-verify-approved`)."""

    def test_a_bypass_is_told_to_the_team_with_what_the_hook_said(self):
        _, text = written(self, ran(self, "hook-bypassed"))

        changed = section(text, "### What changed")
        self.assertIn("The kept Rounds were committed with `--no-verify`: the repo's pre-commit "
                      "hook already failed before this invocation, and the developer approved the "
                      "bypass for it", changed)
        self.assertIn("733 problems found in 412 files", changed)

    def test_a_hook_that_passed_is_only_in_the_detail_log(self):
        _, text = written(self, ran(self, "hook-passed"))

        self.assertNotIn("--no-verify", text)
        self.assertIn("- **Commit hook.** passed: The pre-commit hook .git/hooks/pre-commit "
                      "passes on the unchanged repo, so every keep commit runs it.",
                      text.split("\n## Detail log\n", 1)[1])

    def test_a_ledger_from_before_the_hook_check_says_it_was_not_recorded(self):
        box = ran(self, "reached")
        ledger = next((box.repo / ".agent" / "shopify-speed-tune").glob("*/ledger.json"))
        data = json.loads(ledger.read_text())
        del data["hook"]
        ledger.write_text(json.dumps(data))

        _, text = written(self, box)

        self.assertIn("- **Commit hook.** not recorded.", text.split("\n## Detail log\n", 1)[1])


class ARoundTheSmokeCheckRemovedBeforeItsPairs(unittest.TestCase):
    def setUp(self):
        _, self.text = written(self, ran(self, "smoke-removed"))

    def test_is_told_to_the_team_as_removed_without_being_measured(self):
        self.assertIn("- **P1. Load the hero image eagerly.** Removed in Round 1 without being "
                      "measured, because the smoke check found something broken that works on "
                      "the Control theme.", section(self.text, "### What changed"))

    def test_shows_its_failed_smoke_check_and_no_pairs_in_the_detail_log(self):
        first = section(self.text.split("\n## Detail log\n", 1)[1], "#### Round 1: P1, removed")

        self.assertIn("- **Pairs.** Not measured.", first)
        self.assertIn("- **Smoke check.** round-1 result fail: 2 regressions", first)
        self.assertIn("round-1 product regression add-to-cart: control pass, working fail", first)
        self.assertNotIn("| Page | Pair |", first)


class AReportAfterAnEarlyStop(unittest.TestCase):
    """The invocation stopped in its baseline: only the home page's mobile Measurement holds
    its five Samples. The report is still written, and marks what is missing."""

    def setUp(self):
        self.box = Sandbox(self)
        self.box.start()
        self.box.run("sample", "--page", "home", "--device", "mobile",
                     *sum((["--report", report("home-mobile-%d" % i)] for i in range(1, 6)), []))
        self.result, self.text = written(self, self.box)

    def test_marks_each_figure_never_measured(self):
        self.assertEqual(self.result.lines("REPORT")[0],
                         "REPORT page home before=50 after=- target=- no-target")
        self.assertIn("| Home | 50 (36–56) | – | – | – | no target: no Ceiling |", self.text)
        self.assertIn("| Home | – | – |", self.text)
        self.assertIn("| baseline | Home | desktop | Control | 0 of 5 | – |", self.text)

    def test_says_no_round_ran_and_no_pagespeed_scores_were_given(self):
        self.assertIn("No Round ran: the invocation stopped before its plan.", self.text)
        self.assertIn("The developer's PageSpeed scores were not recorded.", self.text)

    def test_still_names_the_lighthouse_and_chrome_that_took_its_samples(self):
        self.assertIn("Lighthouse 13.5.0 on Chrome for Testing 154.0.8037.57", self.text)

    def test_lives_in_the_skills_agent_folder(self):
        path = Path(re.search(r"(?m)^REPORT file (\S+)$", self.result.out).group(1))

        self.assertEqual(path.name, "report.md")
        self.assertEqual(path.parent.parent,
                         (self.box.repo / ".agent" / "shopify-speed-tune").resolve())


class AStoppedInvocationWithoutItsFinalDesktopMeasurement(unittest.TestCase):
    def test_the_report_names_each_one_to_take(self):
        # Requested 40: every page is past its target before the first Round.
        box = approved(self, ITEMS, "--score", "40")
        box.run("round")

        result = box.run("report")

        self.assertEqual(result.code, 0, result)
        self.assertIn("NOTE the home page's final desktop Measurement holds 0 of 5 Samples: take "
                      "it with `final --page home`, then write the report again", result.out)
        self.assertEqual(len([l for l in result.lines("NOTE") if "final desktop" in l]), 3)


class WhileARoundIsOpen(unittest.TestCase):
    def test_the_report_waits_for_its_verdict(self):
        box = pushed(self)

        result = box.run("report")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED round-open: ")
        self.assertEqual(list((box.repo / ".agent").rglob("report.md")), [])


def missed_lines(result):
    return [l for l in result.lines("REPORT") if l.startswith("REPORT missed ")]


def section(text, heading):
    """The text under one heading, up to the next heading of the same or a higher level."""
    level = heading.split(" ", 1)[0]
    body = text.split(heading + "\n", 1)[1]
    ends = [body.find("\n%s " % ("#" * n)) for n in range(1, len(level) + 1)]
    ends = [e for e in ends if e >= 0]
    return body[:min(ends)] if ends else body


def explanations(box, entries):
    path = box.root / "missed.json"
    path.write_text(json.dumps(entries))
    return path


EXPLAINED = {
    "home": {"reason": "The hero image still waits on a theme script; the eager-image change "
                       "won on home but the Ceiling leaves 9 points for the rest of the theme.",
             "next": [{"change": "Preload the hero image after the viewport tag",
                       "cause": "the LCP image is discovered late",
                       "effect": "+2 to +4 on home"}]},
    "collection": {"reason": "No item targeted the collection grid's own images.",
                   "next": [{"change": "Load the first row of product cards eagerly",
                             "cause": "the first card images are lazy", "effect": "unmeasured"}]},
    "product": {"reason": "Apps hold the product page's main thread.",
                "next": [{"change": "Raise the reviews app's cost with the merchant",
                          "cause": "it is the costliest app on the product page",
                          "effect": "unmeasured: the merchant's decision"}]},
}


if __name__ == "__main__":
    unittest.main()
