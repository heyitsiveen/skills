"""The verdict: the program keeps a Round's change only when it wins clearly and breaks nothing.

A change is kept only when all of these hold:
- every smoke check that passes on the Control theme passes on the Working theme
- no console error or Liquid error appears that the Control theme lacks
- it wins at least 4 of the 5 pairs on at least one of its target pages, and a
  tie is not a win
- no page loses 4 or more of its 5 pairs
- no page's median accessibility score is lower on the Working theme

The smoke check comes first, so a Round it fails is removed without pairs.

Each case below is the real reports and the real smoke results with the one
field edited that makes the case. Plan item P1 targets the home page only.
"""

import unittest

from round_support import (CONTROL, LAZY, LOSS_3, LOSS_4, NEUTRAL, WIN_3, WIN_3_TIE_2, WIN_4,
                           WORKING, add_to_cart_fails, app_block_gone, checked, measure,
                           new_console_error, new_liquid_error, pushed, record_pairs)


class TheVerdict(unittest.TestCase):
    def setUp(self):
        self.box = pushed(self)

    def verdict(self, gains, accessibility=None):
        checked(self.box)
        measure(self.box, gains, accessibility)
        result = self.box.run("verdict")
        self.assertEqual(result.code, 0, result)
        return result.lines("VERDICT")

    def test_four_wins_in_five_on_its_target_page_keep_the_change(self):
        self.assertEqual(self.verdict({"home": WIN_4}), ["VERDICT 1 keep item=P1 won=home"])

    def test_three_wins_in_five_remove_it(self):
        self.assertEqual(self.verdict({"home": WIN_3}),
                         ["VERDICT 1 remove item=P1 reasons=no-win"])

    def test_a_tie_is_not_a_win(self):
        self.assertEqual(self.verdict({"home": WIN_3_TIE_2}),
                         ["VERDICT 1 remove item=P1 reasons=no-win"])

    def test_wins_on_a_page_the_item_does_not_target_do_not_count(self):
        self.assertEqual(self.verdict({"home": WIN_3, "collection": (3, 3, 3, 3, 3)}),
                         ["VERDICT 1 remove item=P1 reasons=no-win"])

    def test_four_losses_in_five_on_any_page_remove_it(self):
        self.assertEqual(self.verdict({"home": WIN_4, "collection": LOSS_4}),
                         ["VERDICT 1 remove item=P1 reasons=loss:collection"])

    def test_three_losses_elsewhere_do_not(self):
        self.assertEqual(self.verdict({"home": WIN_4, "collection": LOSS_3}),
                         ["VERDICT 1 keep item=P1 won=home"])

    def test_a_lower_median_accessibility_score_on_any_page_removes_it(self):
        self.assertEqual(self.verdict({"home": WIN_4}, accessibility={"product": -1}),
                         ["VERDICT 1 remove item=P1 reasons=accessibility:product"])

    def test_every_reason_is_named(self):
        self.assertEqual(
            self.verdict({"home": WIN_3, "product": LOSS_4}, accessibility={"collection": -2}),
            ["VERDICT 1 remove item=P1 reasons=no-win,loss:product,accessibility:collection"])

    def test_the_verdict_shows_each_pages_pairs_first(self):
        checked(self.box)
        measure(self.box, {"home": WIN_4, "collection": LOSS_3})

        result = self.box.run("verdict")

        self.assertEqual(result.lines("PAIRS"), [
            "PAIRS 1 home wins=4 losses=1 ties=0 performance=50->52 accessibility=94->94",
            "PAIRS 1 collection wins=0 losses=3 ties=2 performance=61->60 accessibility=95->95",
            "PAIRS 1 product wins=0 losses=0 ties=5 performance=44->44 accessibility=94->94",
        ])


class AFailedSmokeCheckRemovesTheRoundWithoutPairs(unittest.TestCase):
    def setUp(self):
        self.box = pushed(self)

    def verdict(self, smoke):
        checked(self.box, smoke)
        result = self.box.run("verdict")
        self.assertEqual(result.code, 0, result)
        return result

    def test_a_check_that_passes_only_on_the_control_theme_removes_it(self):
        self.assertEqual(self.verdict(add_to_cart_fails).lines("VERDICT"),
                         ["VERDICT 1 remove item=P1 reasons=smoke-regression"])

    def test_an_app_block_missing_on_the_working_theme_removes_it(self):
        self.assertEqual(self.verdict(app_block_gone).lines("VERDICT"),
                         ["VERDICT 1 remove item=P1 reasons=smoke-regression"])

    def test_a_new_console_error_removes_it(self):
        self.assertEqual(self.verdict(new_console_error).lines("VERDICT"),
                         ["VERDICT 1 remove item=P1 reasons=new-error"])

    def test_a_new_liquid_error_removes_it(self):
        self.assertEqual(self.verdict(new_liquid_error).lines("VERDICT"),
                         ["VERDICT 1 remove item=P1 reasons=new-error"])

    def test_the_round_is_put_back_and_marked_not_measured(self):
        result = self.verdict(add_to_cart_fails)

        self.assertEqual(result.lines("SMOKE"), ["SMOKE round-1 result fail: 2 regressions"])
        self.assertEqual(result.lines("PAIRS"), [])
        self.assertEqual((self.box.repo / "snippets" / "image.liquid").read_text(), LAZY)
        self.assertEqual(self.box.theme_files(WORKING), self.box.theme_files(CONTROL))
        status = self.box.run("status")
        self.assertIn("ROUND 1 removed item=P1 not-measured", status.lines("ROUND"))
        self.assertNotIn("MEASUREMENT round-1", status.out)


class AVerdictNeedsTheWholeRound(unittest.TestCase):
    def test_it_is_refused_until_the_smoke_check_ran(self):
        box = pushed(self)

        result = box.run("verdict")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED round-unchecked: ")
        self.assertEqual(result.lines("VERDICT"), [])

    def test_it_is_refused_until_every_page_holds_five_pairs(self):
        box = pushed(self)
        checked(box)
        record_pairs(box, "home", WIN_4)

        result = box.run("verdict")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED round-unmeasured: ")
        self.assertEqual(result.lines("VERDICT"), [])

    def test_a_measured_and_checked_round_is_not_removed_on_request(self):
        box = pushed(self)
        checked(box)
        measure(box, {"home": WIN_4})

        result = box.run("verdict", "--remove")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED round-measured: ")
        self.assertEqual(box.run("verdict").lines("VERDICT"), ["VERDICT 1 keep item=P1 won=home"])


if __name__ == "__main__":
    unittest.main()
