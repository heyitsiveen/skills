"""Diagnosis: what the baseline Samples already say, read without taking another Sample.

The cost figures are worked by hand from the real reports' third-party summary:
each is the median of the page's five baseline mobile Samples, with a Sample
that loaded nothing from the app or tag counting as zero. Main-thread time is
in ms, transfer size in KiB (1,024 bytes). For example, Google Tag Manager on
the home page:

    main thread  108.93 103.47 86.16 101.21 89.41  -> 101 ms
    transfer     509938 552798 552775 552800 509951 -> 552775 B = 540 KiB

Shopify app extensions are split out of Lighthouse's "Shopify" row by their
/extensions/<id>/<handle>-<version>/ folder: gsc-instagram-feed on the home
page is 19.45 ms (median of 19.45 33.1 16.85 22.09 17.96) and 71,860 B.
"""

import unittest

from plan_support import measured


class AppAndTagCosts(unittest.TestCase):
    def setUp(self):
        self.box = measured(self)
        self.result = self.box.run("diagnose")
        self.assertEqual(self.result.code, 0, self.result)

    def test_each_app_and_tag_costs_its_median_over_each_pages_baseline_samples(self):
        costs = self.result.lines("COST")

        self.assertIn("COST Google Tag Manager | home 101 ms 540 KiB | collection 93 ms 540 KiB "
                      "| product 100 ms 540 KiB", costs)
        self.assertIn("COST ContentSquare | home 114 ms 159 KiB | collection - | product -", costs)

    def test_a_shopify_app_extension_gets_its_own_row(self):
        self.assertIn("COST gsc-instagram-feed (Shopify app) | home 19 ms 70 KiB | collection 8 ms "
                      "64 KiB | product 8 ms 63 KiB", self.result.lines("COST"))

    def test_the_costliest_row_comes_first(self):
        self.assertTrue(self.result.lines("COST")[0].startswith("COST ContentSquare | "))

    def test_the_cost_table_takes_no_extra_samples(self):
        self.assertEqual(self.result.lines("SAMPLE"), [])
        self.assertNotIn("taken", self.box.store()["lighthouse"], "Lighthouse ran")


class FindingsFromTheReports(unittest.TestCase):
    """Each page's own Lighthouse findings, as medians of its five baseline Samples.

    Worked by hand from the home page's reports:

        LCP subparts (ms)  time to first byte 35.8 29.6 30.9 49.7 223.5 -> 36
                           resource load delay 2006.8 694.6 397.1 463.0 488.8 -> 489
                           resource load duration 16.6 11.1 12.2 15.2 11.6 -> 12
                           element render delay 14.3 31.6 38.9 100.4 19.6 -> 32
        render-blocking    22 requests, 16 of them the theme's; FCP saving
                           900 1250 1300 450 450 -> 900 ms
        long tasks (ms)    googletagmanager 574 552 354 437 324 -> 437
                           facebook 285 285 285 313 297 -> 285
                           web pixels 187 226 165 207 179 -> 187
                           the page's HTML 145 207 200 184 137 -> 184

    and the product page's layout shifts: CLS 0.0026 0.0043 0.0040 0.0040 0.0043
    -> 0.004, from the title container (0.0026 in all five Samples).
    """

    def setUp(self):
        self.box = measured(self)
        self.result = self.box.run("diagnose")
        self.findings = self.result.lines("FINDING")

    def finding(self, page, kind):
        prefix = "FINDING %s %s" % (page, kind)
        return next(line for line in self.findings if line.startswith(prefix))

    def test_the_lcp_element_its_breakdown_and_its_discovery(self):
        self.assertEqual(self.finding("home", "lcp"), (
            "FINDING home lcp: image https://store.example/cdn/shop/files/image-31.png, element "
            "div.section-bleed > div.section > div#responsive-image-id1__media_hero > "
            "img.responsive-image, in 5 of 5 Samples; it waits for a lazy-loader script | "
            "time to first byte 36 ms, resource load delay 489 ms, resource load duration 12 ms, "
            "element render delay 32 ms (medians, unthrottled) | discovery fails: "
            "fetchpriority=high should be applied; Request is discoverable in initial document; "
            "LCP resources should not use loading=lazy"))

    def test_the_render_blocking_requests_by_owner(self):
        self.assertTrue(self.finding("home", "render-blocking").startswith(
            "FINDING home render-blocking: 22 requests hold the first paint (median saving FCP "
            "900 ms, LCP 0 ms); theme 16 ("), self.findings)

    def test_the_long_tasks_by_owner(self):
        self.assertTrue(self.finding("home", "long-tasks").startswith(
            "FINDING home long-tasks (median ms per Sample, simulated): www.googletagmanager.com "
            "437, connect.facebook.net 285, Shopify web pixels 187, the page's HTML 184, "), self.findings)

    def test_the_layout_shifts_by_element(self):
        self.assertTrue(self.finding("product", "layout-shift").startswith(
            "FINDING product layout-shift: CLS 0.004 (median); div.pdp-title-container 0.003 in "
            "5 of 5, "), self.findings)


if __name__ == "__main__":
    unittest.main()
