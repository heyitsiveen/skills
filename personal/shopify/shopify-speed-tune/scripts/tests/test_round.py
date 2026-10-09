"""A Round may use only an item of the approved plan, and each item only once."""

import unittest

from plan_support import diagnosed, write_items

ITEMS = [
    {"change": "Batch the header-height script's layout reads behind one ResizeObserver",
     "pages": ["home"], "cause": "forced reflows from the inline header script",
     "effect": "TBT steadier"},
    {"change": "Lazy-load the footer's payment icons", "pages": ["product"],
     "cause": "icons fetched before the gallery", "effect": "+0 to +1"},
]


class BeforeApproval(unittest.TestCase):
    def test_a_round_is_refused(self):
        box = diagnosed(self)
        box.run("plan", "--items", write_items(box, ITEMS))

        result = box.run("round", "--item", "P1")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED plan-not-approved: ")


class AfterApproval(unittest.TestCase):
    def setUp(self):
        self.box = diagnosed(self)
        self.box.run("plan", "--items", write_items(self.box, ITEMS))
        approved = self.box.run("plan", "--approve")
        self.assertEqual(approved.code, 0, approved)

    def test_a_planned_unused_item_opens_a_round(self):
        result = self.box.run("round", "--item", "P2")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("ROUND"), ["ROUND 1 opened item=P2 pages=product"])

    def test_an_item_outside_the_plan_is_refused(self):
        result = self.box.run("round", "--item", "P3")

        self.assertEqual(result.code, 1, result)
        self.assertEqual(result.lines("REFUSED"),
                         ["REFUSED unplanned-item: P3 is not in the approved plan (P1, P2)"])
        self.assertEqual(result.lines("ROUND"), [])

    def test_an_item_already_used_is_refused(self):
        self.box.run("round", "--item", "P1")

        result = self.box.run("round", "--item", "P1")

        self.assertEqual(result.code, 1, result)
        self.assertEqual(result.lines("REFUSED"), ["REFUSED item-used: P1 was already used by Round 1"])
        self.assertIn("PLAN approved items=2 used=1", self.box.run("status").lines("PLAN"))


if __name__ == "__main__":
    unittest.main()
