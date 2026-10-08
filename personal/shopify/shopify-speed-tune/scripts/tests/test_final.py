"""The final desktop Measurement: each page once more on desktop, at the end.

Desktop decides nothing. It is measured in the baseline, on the Control theme,
and again once the Rounds are over, on the Working theme, which then holds
every kept Round and nothing else: the theme the developer publishes.
"""

import unittest

from round_support import pushed
from support import Sandbox


class TheFinalDesktopMeasurement(unittest.TestCase):
    def test_takes_five_desktop_samples_of_the_page_on_the_working_theme(self):
        box = Sandbox(self)
        box.start()

        result = box.run("final", "--page", "home")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(len(result.lines("SAMPLE")), 5)
        self.assertRegex(result.out, r"(?m)^MEASUREMENT final home desktop working n=5 \| "
                                     r"performance 88 \[88-88\] \| ")

    def test_is_finished_by_running_it_again_after_a_cut_off_call(self):
        box = Sandbox(self)
        box.start()
        box.run("final", "--page", "home", "--count", "2")

        result = box.run("final", "--page", "home")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(len(result.lines("SAMPLE")), 3)
        self.assertRegex(result.out, r"(?m)^MEASUREMENT final home desktop working n=5 ")

    def test_waits_while_a_round_is_open(self):
        box = pushed(self)

        result = box.run("final", "--page", "home")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED round-open: ")
        self.assertEqual(result.lines("SAMPLE"), [])


if __name__ == "__main__":
    unittest.main()
