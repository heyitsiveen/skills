"""The baseline report: each page's medians and ranges, and the versions that measured them."""

import re
import unittest
from pathlib import Path

from support import Sandbox, report


class BaselineReport(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox(self)
        self.box.start()
        self.box.run("sample", "--page", "home", "--device", "mobile",
                     *sum((["--report", report("home-mobile-%d" % i)] for i in range(1, 6)), []))

    def write(self):
        result = self.box.run("report")
        self.assertEqual(result.code, 0, result)
        path = re.search(r"^REPORT (\S+)$", result.out, re.M).group(1)
        return Path(path).read_text()

    def test_it_gives_each_measurement_as_its_median_and_range(self):
        text = self.write()

        self.assertIn("| Home | mobile | 50 (36–56) | 10.2 s (9.4–11.0) | 672 ms (430–1,315) "
                      "| 0.000 (0.000–0.000) | 3.7 s (3.6–5.2) | 3.8 s (3.7–5.6) | 94 (94–94) |", text)
        self.assertIn("| Home | desktop | not measured (0 of 5 Samples) |", text)

    def test_it_names_the_lighthouse_and_chrome_versions(self):
        text = self.write()

        self.assertIn("Lighthouse 13.5.0", text)
        self.assertIn("Chrome for Testing 154.0.8037.57", text)

    def test_it_lives_in_the_skills_agent_folder(self):
        result = self.box.run("report")

        path = Path(re.search(r"^REPORT (\S+)$", result.out, re.M).group(1))
        self.assertEqual(path.parent.parent, (self.box.repo / ".agent" / "shopify-speed-tune").resolve())


if __name__ == "__main__":
    unittest.main()
