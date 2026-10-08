"""The plan: what the developer approves at the skill's only stop.

The plan shows each page's baseline median and range, its Ceiling and its
target, the baseline smoke check, the app and tag cost table, and the plan
items in order: known Golden theme defects first, then the rest in the order
given. Approval makes it final.
"""

import re
import unittest
from pathlib import Path

from plan_support import (DEFECTIVE, PAGES, ceiling_reports, diagnosed, measured, record,
                          write_items)
from round_support import app_block_gone, checked

ITEMS = [
    {"change": "Batch the header-height script's layout reads behind one ResizeObserver",
     "pages": ["home", "collection", "product"],
     "cause": "forced reflows from the inline header script on every header mutation",
     "effect": "TBT steadier; +2 to +4 where it fires"},
    {"change": "Render the first section's image eagerly, with a real src, srcset and sizes",
     "pages": ["home", "collection", "product"],
     "cause": "the LCP image waits for lazysizes; lazy_loading ignores false; the srcset drops "
              "its widest candidate",
     "effect": "LCP load delay gone; +10 to +18 on each page",
     "defects": ["D1", "D2", "D3"]},
    {"change": "Serve the button snippet's CSS once through {% stylesheet %}",
     "pages": ["home", "collection", "product"],
     "cause": "12.1 KB of static CSS repeated for every button",
     "effect": "+0 to +2",
     "defects": ["D4"]},
]


def item_heads(result):
    return [line.split(" pages=")[0] for line in result.lines("PLAN") if line.startswith("PLAN item ")]


class ThePlanShowsWhatTheDeveloperApproves(unittest.TestCase):
    def setUp(self):
        self.box = diagnosed(self, theme_files=DEFECTIVE)
        self.result = self.box.run("plan", "--items", write_items(self.box, ITEMS))
        self.assertEqual(self.result.code, 0, self.result)

    def test_known_defects_come_first_then_the_rest_in_the_order_given(self):
        self.assertEqual(item_heads(self.result),
                         ["PLAN item P1 known=D1,D2,D3", "PLAN item P2 known=D4", "PLAN item P3"])

    def test_each_item_states_its_change_pages_cause_and_effect(self):
        self.assertIn(
            "PLAN item P3 pages=home,collection,product | change: Batch the header-height script's "
            "layout reads behind one ResizeObserver | cause: forced reflows from the inline header "
            "script on every header mutation | effect: TBT steadier; +2 to +4 where it fires",
            self.result.lines("PLAN"))

    def test_each_page_shows_its_baseline_ceiling_and_target(self):
        pages = [line for line in self.result.lines("PLAN") if line.startswith("PLAN page ")]

        self.assertEqual(pages, PAGE_LINES)

    def test_the_cost_table_comes_with_it(self):
        self.assertEqual(self.result.lines("COST")[0],
                         "COST ContentSquare | home 114 ms 159 KiB | collection - | product -")

    def test_it_is_written_down_for_the_developer(self):
        path = Path(re.search(r"(?m)^PLAN file (\S+)$", self.result.out).group(1))
        text = path.read_text()

        self.assertEqual(path.name, "plan.md")
        for needed in ("| Home | https://store.example/ |", "## Apps and tags", "**P1**",
                       "Serve the button snippet's CSS once through {% stylesheet %}"):
            self.assertIn(needed, text)

    def test_it_is_a_draft_until_approved(self):
        self.assertEqual(self.result.lines("PLAN")[-1], "PLAN draft items=3")


class ThePlanCarriesTheBaselineSmokeCheck(unittest.TestCase):
    """A Round whose smoke check fails is removed unmeasured, so the developer approves the
    plan knowing whether the check holds on this store: its baseline SMOKE lines are in the
    plan's Pages section, judged by the rule in force when the plan is shown."""

    def plan(self, box):
        result = box.run("plan", "--items", write_items(box, ITEMS[:1]))
        self.assertEqual(result.code, 0, result)
        text = Path(re.search(r"(?m)^PLAN file (\S+)$", result.out).group(1)).read_text()
        return result, text.split("\n## Pages\n", 1)[1].split("\n## Apps and tags\n", 1)[0]

    def test_a_check_the_two_copies_already_fail_comes_with_what_it_found(self):
        box = diagnosed(self)
        checked(box, app_block_gone)

        result, pages = self.plan(box)

        found = ["SMOKE baseline product missing-app-block: "
                 "shopify-block-AProdControlTokenQ__example_restock_app_restock_form_Pz8Lm3",
                 "SMOKE baseline result fail: 1 missing app block"]
        self.assertEqual(result.lines("SMOKE"), found)
        for line in found:
            self.assertIn(line, pages)

    def test_stored_results_read_by_the_rule_in_force(self):
        box = diagnosed(self)
        checked(box)  # each section app block with its own theme's token, as the store renders it

        result, pages = self.plan(box)

        self.assertEqual(result.lines("SMOKE"), ["SMOKE baseline result pass"])
        self.assertIn("SMOKE baseline result pass", pages)

    def test_a_plan_with_no_baseline_check_says_so(self):
        box = diagnosed(self)

        result, pages = self.plan(box)

        self.assertEqual(result.lines("SMOKE"), [])
        self.assertIn("No baseline smoke result is recorded", pages)


class ADraftPlanIsChecked(unittest.TestCase):
    def setUp(self):
        self.box = diagnosed(self, theme_files=DEFECTIVE)

    def plan(self, items):
        return self.box.run("plan", "--items", write_items(self.box, items))

    def test_an_item_without_its_cause_is_refused(self):
        result = self.plan([dict(ITEMS[0], cause="")])

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED bad-plan: item 1 states no cause$")

    def test_an_item_on_an_unknown_page_is_refused(self):
        result = self.plan([dict(ITEMS[0], pages=["home", "cart"])])

        self.assertRegex(result.out, r"(?m)^REFUSED bad-plan: item 1's pages must be ")

    def test_a_defect_the_diagnosis_did_not_find_is_refused(self):
        result = self.plan([dict(ITEMS[2], defects=["D7"])])

        self.assertRegex(result.out, r"(?m)^REFUSED bad-plan: item 1 names D7, which diagnose "
                                     r"did not find$")


class AStoreNotOnGolden(unittest.TestCase):
    def test_plans_from_the_findings_alone(self):
        box = diagnosed(self)

        result = box.run("plan", "--items", write_items(box, [ITEMS[0]]))

        self.assertEqual(result.code, 0, result)
        self.assertEqual(item_heads(result), ["PLAN item P1"])


class Approval(unittest.TestCase):
    def setUp(self):
        self.box = diagnosed(self, theme_files=DEFECTIVE)
        self.box.run("plan", "--items", write_items(self.box, ITEMS))

    def test_approval_records_the_plan(self):
        result = self.box.run("plan", "--approve")

        self.assertEqual(result.code, 0, result)
        self.assertRegex(result.out, r"(?m)^PLAN approved items=3 at \S+$")
        self.assertIn("PLAN approved items=3 used=0", self.box.run("status").lines("PLAN"))

    def test_an_approved_plan_is_final(self):
        self.box.run("plan", "--approve")

        result = self.box.run("plan", "--items", write_items(self.box, ITEMS[:1]))

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED plan-approved: ")

    def test_the_pages_it_was_measured_on_are_fixed_too(self):
        self.box.run("plan", "--approve")

        result = self.box.run("pages", "--collection", "/collections/another")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED plan-approved: ")
        self.assertIn("PAGE collection https://store.example/collections/example-collection",
                      self.box.run("status").lines("PAGE"))


class APlanNeedsTheCeilingsAndTheDiagnosis(unittest.TestCase):
    def test_a_plan_before_the_ceilings_is_refused(self):
        box = measured(self, theme_files=DEFECTIVE)
        box.run("diagnose")

        result = box.run("plan", "--items", write_items(box, ITEMS))

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED no-ceiling: the home page's Ceiling ")

    def test_a_plan_before_the_diagnosis_is_refused(self):
        box = measured(self, theme_files=DEFECTIVE)
        for page in PAGES:
            record(box, "ceiling", page, ceiling_reports(page))

        result = box.run("plan", "--items", write_items(box, ITEMS))

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED no-diagnosis: ")


# Worked by hand from the real reports. The baseline medians and ranges are
# test_psi.py's; the Ceiling Samples' Performance scores are
#   home        59 63 58 65 58  -> 59 (58-65)
#   collection  75 71 82 70 69  -> 71 (69-82)
#   product     68 59 64 65 66  -> 65 (59-68)
# and the requested score, 80, is above every Ceiling, so each target is its Ceiling.
PAGE_LINES = [
    "PLAN page home https://store.example/ baseline=50 [36-56] ceiling=59 [58-65] target=59",
    "PLAN page collection https://store.example/collections/example-collection baseline=61 "
    "[46-64] ceiling=71 [69-82] target=71",
    "PLAN page product https://store.example/products/example-product baseline=44 [43-46] "
    "ceiling=65 [59-68] target=65",
]


if __name__ == "__main__":
    unittest.main()
