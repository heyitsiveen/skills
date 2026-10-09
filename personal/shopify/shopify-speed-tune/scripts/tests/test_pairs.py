"""A Round's measurement: five interleaved pairs on each of the three pages.

Each pair is one Control theme Sample, then one Working theme Sample, taken
back to back, so store and network conditions meet both themes alike. A pair is
a win when the Working theme's Performance score is higher, a loss when lower,
and a tie otherwise.
"""

import re
import unittest

from round_support import (WORKING, add_to_cart_fails, checked, opened, pair_files, pushed,
                           record_pairs, write)


class RecordingPairsFromReportFiles(unittest.TestCase):
    def setUp(self):
        self.box = pushed(self)
        checked(self.box)

    def test_each_pair_is_a_win_a_loss_or_a_tie_on_the_performance_score(self):
        # The home page's real scores are 36, 49, 56, 50 and 55.
        result = record_pairs(self.box, "home", (3, 0, -2, 1, 4))

        self.assertEqual(result.lines("PAIR"), [
            "PAIR 1 home 1 control=36 working=39 win",
            "PAIR 1 home 2 control=49 working=49 tie",
            "PAIR 1 home 3 control=56 working=54 loss",
            "PAIR 1 home 4 control=50 working=51 win",
            "PAIR 1 home 5 control=55 working=59 win",
        ])
        self.assertEqual(result.lines("PAIRS"), [
            "PAIRS 1 home wins=3 losses=1 ties=1 performance=50->51 accessibility=94->94",
            "PAIRS 1 incomplete home=5/5 collection=0/5 product=0/5",
        ])

    def test_the_round_has_a_measurement_per_theme_and_page(self):
        record_pairs(self.box, "collection", (0, 0, 0, 0, 0))

        status = self.box.run("status")

        self.assertRegex(status.out, r"(?m)^MEASUREMENT round-1 collection mobile control n=5 \| "
                                     r"performance 61 \[46-64\] ")
        self.assertRegex(status.out, r"(?m)^MEASUREMENT round-1 collection mobile working n=5 \| "
                                     r"performance 61 \[46-64\] ")

    def test_a_page_takes_five_pairs_and_no_more(self):
        record_pairs(self.box, "product", (1, 1, 1, 1, 1))
        control, working = pair_files(self.box, "product", (1,))[0]

        result = self.box.run("pairs", "--page", "product", "--pair", control, working)

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED pairs-complete: the product page already "
                                     r"holds 5 pairs")


class PairsNeedThePushedChange(unittest.TestCase):
    def test_no_pair_is_taken_before_the_change_is_pushed(self):
        box = opened(self)

        result = box.run("pairs")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED round-not-pushed: ")

    def test_no_pair_is_taken_once_the_tree_differs_from_what_was_pushed(self):
        box = pushed(self)
        write(box, "assets/theme.js", "/* changed after the push */\n")

        result = box.run("pairs")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED changed-since-push: ")


class PairsFollowAPassingSmokeCheck(unittest.TestCase):
    """The smoke check runs first: it warms the store's cache with the changed files and
    catches a broken change before fifteen minutes of pairs."""

    def test_no_pair_is_taken_before_the_rounds_smoke_check(self):
        box = pushed(self)

        result = box.run("pairs")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED round-unchecked: Round 1 has no smoke check yet")
        self.assertEqual(result.lines("SAMPLE"), [])

    def test_no_pair_is_taken_after_a_failed_one(self):
        box = pushed(self)
        checked(box, add_to_cart_fails)

        result = box.run("pairs")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED smoke-failed: Round 1's smoke check failed")
        self.assertEqual(result.lines("SAMPLE"), [])


class TakingPairs(unittest.TestCase):
    """The fake Lighthouse serves the theme whose preview cookie is in its Chrome's
    jar, from that theme's own asset folder."""

    def setUp(self):
        self.box = pushed(self)
        checked(self.box)

    def taken(self, result):
        """(page, theme) of each Sample recorded, in order; a rejected one is not."""
        found = [re.match(r"SAMPLE s\d+ round-1 (\w+) mobile (\w+) ", line)
                 for line in result.lines("SAMPLE")]
        return [m.groups() for m in found if m]

    def assert_back_to_back(self, result):
        """Each PAIR line comes straight after its two Samples: its Control Sample, then its
        Working Sample, with nothing between them."""
        lines = result.out.splitlines()
        pairs = [n for n, line in enumerate(lines) if line.startswith("PAIR ")]
        self.assertTrue(pairs, result)
        for n in pairs:
            page = lines[n].split()[2]
            halves = [re.match(r"SAMPLE s\d+ round-1 (\w+) mobile (\w+) ", line)
                      for line in lines[n - 2:n]]
            self.assertEqual([m.groups() if m else None for m in halves],
                             [(page, "control"), (page, "working")], result)

    def test_pairs_alternate_control_then_working_and_go_round_the_pages(self):
        result = self.box.run("pairs")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(self.taken(result)[:8], [
            ("home", "control"), ("home", "working"),
            ("collection", "control"), ("collection", "working"),
            ("product", "control"), ("product", "working"),
            ("home", "control"), ("home", "working")])
        self.assertEqual(len(result.lines("PAIR")), 15)
        self.assertEqual(result.lines("PAIRS")[-1], "PAIRS 1 complete")

    def test_a_call_out_of_time_stops_between_pairs_and_the_next_one_goes_on(self):
        first = self.box.run("pairs", "--minutes", "0")

        self.assertEqual(first.code, 0, first)
        self.assertEqual(len(first.lines("PAIR")), 1)
        self.assertEqual(first.lines("PAIRS"),
                         ["PAIRS 1 incomplete home=1/5 collection=0/5 product=0/5"])

        second = self.box.run("pairs", "--minutes", "0")

        self.assertEqual(second.lines("PAIR")[0][:19], "PAIR 1 collection 1")

    def test_both_preview_cookies_come_before_a_pair_so_no_pause_falls_inside_it(self):
        # The store answers the Working theme's preview request with HTTP 429 once, as it did
        # a real Round: the program waits and asks again.
        self.box.edit_store(lambda s: s.update(
            too_many_requests_on={"preview_theme_id=%d" % WORKING: 1}))

        result = self.box.run("pairs", "--page", "home", "--minutes", "0")

        self.assertEqual(result.code, 0, result)
        self.assertEqual([line.split(" ", 1)[0] for line in result.out.splitlines()],
                         ["NOTE", "SAMPLE", "SAMPLE", "PAIR", "PAIRS"], result)
        self.assertIn("preview_theme_id=%d answered HTTP 429" % WORKING, result.lines("NOTE")[0])
        self.assert_back_to_back(result)

    def test_a_working_sample_rejected_after_its_control_sample_retakes_the_pair_whole(self):
        # The rejected Sample took a whole Sample's time after the Control Sample.
        self.box.edit_store(lambda s: s["lighthouse"].update(drops_cookie_once_of=[WORKING]))

        result = self.box.run("pairs", "--page", "home", "--minutes", "0")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(self.taken(result), [("home", "control"), ("home", "control"),
                                              ("home", "working")])
        self.assert_back_to_back(result)
        set_aside = re.match(r"SAMPLE (s\d+) ", result.lines("SAMPLE")[0]).group(1)
        self.assertIn("NOTE pair 1 on the home page is retaken whole: its Working Sample was "
                      "rejected, so its Control Sample %s is set aside" % set_aside,
                      result.lines("NOTE"))
        status = self.box.run("status")
        self.assertRegex(status.out, r"(?m)^MEASUREMENT round-1 home mobile control incomplete 1/5")

    def test_a_working_sample_that_cannot_be_taken_discards_its_control_sample(self):
        self.box.edit_store(lambda s: s["lighthouse"].update(drops_cookie_of=[200]))

        failed = self.box.run("pairs", "--page", "home")

        self.assertEqual(failed.code, 1, failed)
        self.assertRegex(failed.out, r"(?m)^FAILED samples-rejected: ")
        self.assertEqual(failed.lines("PAIR"), [])
        status = self.box.run("status")
        self.assertIn("MEASUREMENT round-1 home mobile control incomplete 0/5", status.out)

        self.box.edit_store(lambda s: s["lighthouse"].update(drops_cookie_of=[]))
        again = self.box.run("pairs", "--page", "home", "--minutes", "0")

        self.assertEqual(again.lines("PAIR")[0][:13], "PAIR 1 home 1")


if __name__ == "__main__":
    unittest.main()
