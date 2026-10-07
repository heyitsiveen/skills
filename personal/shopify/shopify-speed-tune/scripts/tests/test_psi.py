"""The PageSpeed comparison: the developer's three PageSpeed mobile scores against
the matching baseline medians, warning when any gap is more than 10 points.

The baseline medians of the real reports, worked by hand:

    home        36 49 56 50 55  -> 50
    collection  46 64 61 60 61  -> 61
    product     46 43 46 43 44  -> 44
"""

import unittest

from plan_support import measured


class PageSpeedComparison(unittest.TestCase):
    def setUp(self):
        self.box = measured(self)

    def psi(self, home, collection, product):
        result = self.box.run("psi", "--home", home, "--collection", collection, "--product", product)
        self.assertEqual(result.code, 0, result)
        return result

    def test_each_score_is_set_beside_its_pages_baseline_median(self):
        result = self.psi(50, 58, 47)

        self.assertEqual(result.lines("PSI"), [
            "PSI home pagespeed=50 baseline=50 gap=0",
            "PSI collection pagespeed=58 baseline=61 gap=-3",
            "PSI product pagespeed=47 baseline=44 gap=+3",
        ])

    def test_a_gap_just_above_10_points_warns(self):
        result = self.psi(61, 50, 44)

        warned = [line.split(":")[0] for line in result.lines("WARN")]
        self.assertEqual(warned, ["WARN psi-gap home", "WARN psi-gap collection"])

    def test_a_gap_of_10_points_or_just_below_stays_silent(self):
        result = self.psi(60, 51, 53)

        self.assertEqual(result.lines("WARN"), [])
        self.assertIn("PSI home pagespeed=60 baseline=50 gap=+10", result.lines("PSI"))
        self.assertIn("PSI product pagespeed=53 baseline=44 gap=+9", result.lines("PSI"))

    def test_the_comparison_is_kept_for_the_invocation(self):
        self.psi(61, 50, 44)

        status = self.box.run("status").lines("PSI")

        self.assertIn("PSI home pagespeed=61 baseline=50 gap=+11", status)

    def test_a_score_outside_0_to_100_is_refused(self):
        result = self.box.run("psi", "--home", "101", "--collection", "50", "--product", "44")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED bad-score: ")


if __name__ == "__main__":
    unittest.main()
