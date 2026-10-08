"""When the Rounds stop: every page at its target, or no unused plan item left.

After every verdict the program sets each page's current kept-state median
against its target: the Working theme's median when the Round was kept, the
Control theme's when it was removed, the baseline before any Round. It prints
one TARGET line per page, then a STOP line naming its reason, or a NEXT line.
The real pages' targets are home 59, collection 71 and product 65.
"""

import unittest

from round_support import ITEMS, NEUTRAL, WIN_4, apply_item, approved, checked, measure, pushed


def decide(box, gains):
    checked(box)
    measure(box, gains)
    result = box.run("verdict")
    box.test.assertEqual(result.code, 0, result)
    return result


def next_round(box, item):
    result = box.run("round")
    box.test.assertEqual(result.code, 0, result)
    apply_item(box, item)
    result = box.run("push")
    box.test.assertEqual(result.code, 0, result)


# Gains that lift every page's Working median past its target: 50 -> 60 on home,
# 61 -> 72 on collection and 44 -> 66 on product.
PAST_THE_TARGETS = {"home": (10,) * 5, "collection": (11,) * 5, "product": (22,) * 5}


class TheRoundsStop(unittest.TestCase):
    def test_when_every_pages_kept_median_reaches_its_target(self):
        box = pushed(self, item="P2")

        result = decide(box, PAST_THE_TARGETS)

        self.assertEqual(result.lines("TARGET"), [
            "TARGET home kept=60 target=59 reached from=round-1",
            "TARGET collection kept=72 target=71 reached from=round-1",
            "TARGET product kept=66 target=65 reached from=round-1",
        ])
        self.assertEqual(result.lines("STOP"), ["STOP targets-reached"])
        self.assertEqual(result.lines("NEXT"), [])

    def test_when_no_unused_plan_item_remains(self):
        box = pushed(self)
        decide(box, {"home": NEUTRAL})
        next_round(box, "P2")

        result = decide(box, {"home": NEUTRAL})

        self.assertEqual(result.lines("STOP"), ["STOP plan-exhausted"])

    def test_otherwise_the_next_unused_item_follows(self):
        box = pushed(self)

        result = decide(box, {"home": WIN_4})

        self.assertEqual(result.lines("TARGET"), [
            "TARGET home kept=52 target=59 short from=round-1",
            "TARGET collection kept=61 target=71 short from=round-1",
            "TARGET product kept=44 target=65 short from=round-1",
        ])
        self.assertEqual(result.lines("NEXT"), ["NEXT item=P2 unused=1"])
        self.assertEqual(result.lines("STOP"), [])

    def test_a_removed_round_leaves_the_control_themes_medians_as_the_kept_state(self):
        box = pushed(self)

        result = decide(box, {"home": (-3, -3, -3, -3, -3)})

        self.assertEqual(result.lines("VERDICT"), ["VERDICT 1 remove item=P1 reasons=no-win,loss:home"])
        self.assertIn("TARGET home kept=50 target=59 short from=round-1", result.lines("TARGET"))


class BeforeTheFirstRound(unittest.TestCase):
    def test_pages_already_at_their_targets_get_no_round(self):
        # Requested 40: each target is 40, and the baselines are 50, 61 and 44.
        box = approved(self, ITEMS, "--score", "40")

        result = box.run("round")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("TARGET"), [
            "TARGET home kept=50 target=40 reached from=baseline",
            "TARGET collection kept=61 target=40 reached from=baseline",
            "TARGET product kept=44 target=40 reached from=baseline",
        ])
        self.assertEqual(result.lines("STOP"), ["STOP targets-reached"])
        self.assertEqual(result.lines("ROUND"), [])


class AfterTheStop(unittest.TestCase):
    def setUp(self):
        self.box = pushed(self, item="P2")
        decide(self.box, PAST_THE_TARGETS)

    def test_no_round_opens_and_the_stop_line_is_printed_again(self):
        result = self.box.run("round")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("STOP"), ["STOP targets-reached"])
        self.assertEqual(result.lines("ROUND"), [])

    def test_status_shows_every_verdict_the_targets_and_the_stop(self):
        status = self.box.run("status")

        self.assertEqual(status.lines("VERDICT"), ["VERDICT 1 keep item=P2 won=home,collection,product"])
        self.assertIn("TARGET product kept=66 target=65 reached from=round-1", status.lines("TARGET"))
        self.assertEqual(status.lines("STOP"), ["STOP targets-reached"])


if __name__ == "__main__":
    unittest.main()
