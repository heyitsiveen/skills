"""Measurements: five Samples of one page, device and theme, as a median and a range.

The expected figures are worked by hand from the five real home-page reports:

    performance   36 49 56 50 55              -> 50, 36-56
    LCP (ms)      10157.06 9760.60 10246.66 10975.68 9350.11
                                              -> 10157, 9350-10976
    TBT (ms)      1314.5 700.5 430 672 464.5  -> 672, 430-1315
    CLS           0 0 0 0 0                   -> 0.000
    FCP (ms)      5207.91 3742.46 3727.81 3751.53 3567.41
                                              -> 3742, 3567-5208
    Speed Index   5645.78 3742.46 3727.81 3751.53 3817.39
                                              -> 3752, 3728-5646
    accessibility 94 94 94 94 94              -> 94
"""

import unittest

from support import Sandbox, report

HOME_MOBILE = [report("home-mobile-%d" % i) for i in range(1, 6)]
HOME_MOBILE_MEASUREMENT = (
    "MEASUREMENT baseline home mobile control n=5 | performance 50 [36-56] | "
    "lcp 10157ms [9350-10976ms] | tbt 672ms [430-1315ms] | cls 0.000 [0.000-0.000] | "
    "fcp 3742ms [3567-5208ms] | si 3752ms [3728-5646ms] | accessibility 94 [94-94]")


def record(box, page, device, *reports):
    args = ["sample", "--page", page, "--device", device]
    for path in reports:
        args += ["--report", path]
    return box.run(*args)


class MedianAndRange(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox(self)
        self.box.start()

    def test_five_samples_make_a_measurement_with_the_median_and_range_of_each_metric(self):
        record(self.box, "home", "mobile", *HOME_MOBILE)

        status = self.box.run("status")

        self.assertIn(HOME_MOBILE_MEASUREMENT, status.lines("MEASUREMENT"))

    def test_the_fifth_sample_prints_the_measurement(self):
        record(self.box, "home", "mobile", *HOME_MOBILE[:4])

        fifth = record(self.box, "home", "mobile", HOME_MOBILE[4])

        self.assertEqual(fifth.lines("MEASUREMENT"), [HOME_MOBILE_MEASUREMENT])

    def test_fewer_than_five_samples_report_no_median(self):
        record(self.box, "home", "mobile", *HOME_MOBILE[:3])

        status = self.box.run("status")

        self.assertIn("MEASUREMENT baseline home mobile control incomplete 3/5",
                      status.lines("MEASUREMENT"))

    def test_a_sixth_sample_is_refused(self):
        record(self.box, "home", "mobile", *HOME_MOBILE)

        sixth = record(self.box, "home", "mobile", HOME_MOBILE[0])

        self.assertEqual(sixth.code, 1, sixth)
        self.assertRegex(sixth.out, r"(?m)^REFUSED measurement-complete: ")
        self.assertIn(HOME_MOBILE_MEASUREMENT, self.box.run("status").lines("MEASUREMENT"))

    def test_mobile_and_desktop_are_separate_measurements(self):
        record(self.box, "home", "mobile", *HOME_MOBILE)
        record(self.box, "home", "desktop", report("home-desktop-1"))

        measurements = self.box.run("status").lines("MEASUREMENT")

        self.assertIn(HOME_MOBILE_MEASUREMENT, measurements)
        self.assertIn("MEASUREMENT baseline home desktop control incomplete 1/5", measurements)


if __name__ == "__main__":
    unittest.main()
