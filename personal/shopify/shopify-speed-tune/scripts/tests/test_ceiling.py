"""The Ceiling: each page measured with the theme's own optional requests blocked.

The probe blocks theme scripts, theme fonts and every theme image except the
page's LCP image; stylesheets, apps and tags stay. Its patterns are built from
the page's five baseline mobile Samples, so they block what those Samples
actually requested.
"""

import fnmatch
import json
import unittest

from plan_support import PAGES, ceiling_reports, measured, record
from support import built, read_report, report, started

HOME_MOBILE = [report("home-mobile-%d" % i) for i in range(1, 6)]
# Requests the real home page made, as its baseline reports list them.
HERO = "https://store.example/cdn/shop/files/image-31.png?v=1787744830&width=800"
HERO_STUB = "https://store.example/cdn/shop/files/image-31.png?v=1787744830&width=20"
LOGO = "https://store.example/cdn/shop/files/image-32.png?v=1787732311&width=375"
THEME_SCRIPT = ("https://store.example/cdn/shop/t/23/assets/lazysizes.min.js"
                "?v=56805471290311245611787729509")
COMPILED_SCRIPT = ("https://store.example/cdn/shop/t/23/compiled_assets/scripts.js"
                   "?v=24523070562085982091791368346")
THEME_FONT = "https://store.example/cdn/shop/t/23/assets/CaviarDreams.ttf?v=168276437267777086351787734478"
LIBRARY_FONT = ("https://store.example/cdn/fonts/open_sans/"
                "opensans_n5.500dcf21ddee5bc5855ad3a20394d3bc363c217c.woff2")
STYLESHEET = "https://store.example/cdn/shop/t/23/assets/critical.css?v=19156505368130484971787729508"
COMPILED_STYLESHEET = ("https://store.example/cdn/shop/t/23/compiled_assets/styles.css"
                       "?v=40070799103536477801791368346")
APP_SCRIPT = ("https://cdn.shopify.com/extensions/01a11642-41e1-713e-a375-2820e8cde5c7/"
              "gsc-instagram-feed-95/assets/gsc-instafeed-widget.js")
TAG_SCRIPT = "https://www.googletagmanager.com/gtag/js?id=G-EXAMPLE"
PLATFORM_SCRIPT = "https://store.example/cdn/shopifycloud/perf-kit/shopify-perf-kit-3.9.6.min.js"


def blocks(patterns, url):
    """Chromium's rule for Lighthouse's --blocked-url-patterns: a '*' matches any
    run of characters, and every pattern is implicitly wrapped in '*'."""
    for pattern in patterns:
        assert "?" not in pattern and "[" not in pattern, pattern  # fnmatch would read them
        if fnmatch.fnmatchcase(url, "*" + pattern + "*"):
            return True
    return False


def record_baseline(box, page, reports):
    args = ["sample", "--page", page, "--device", "mobile"]
    for path in reports:
        args += ["--report", path]
    result = box.run(*args)
    box.test.assertEqual(result.code, 0, result)


def probe_lines(result, page):
    """The probe as the program prints it: (blocked patterns, protected images)."""
    blocked = [l.split(" ", 3)[3] for l in result.lines("CEILING") if l.startswith("CEILING %s block " % page)]
    protected = [l.split(" ", 3)[3] for l in result.lines("CEILING") if l.startswith("CEILING %s protect " % page)]
    return blocked, protected


class TheCeilingNeedsTheBaseline(unittest.TestCase):
    def test_a_page_without_its_five_baseline_mobile_samples_is_refused(self):
        box, _, _ = started(self)
        record_baseline(box, "home", HOME_MOBILE[:4])

        result = box.run("ceiling", "--page", "home")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED no-baseline: ")
        self.assertEqual(result.lines("SAMPLE"), [])


class TheProbeBlocksTheThemesOptionalRequests(unittest.TestCase):
    def setUp(self):
        # Every test here only reads what the one Ceiling Sample printed.
        def build(test):
            box, _, _ = started(test)
            record_baseline(box, "home", HOME_MOBILE)
            result = box.run("ceiling", "--page", "home", "--count", "1")
            test.assertEqual(result.code, 0, result)
            return box, result

        self.box, self.result = built(self, "ceiling-probe-home", build)
        self.blocked, self.protected = probe_lines(self.result, "home")

    def test_theme_scripts_and_theme_fonts_are_blocked(self):
        for url in (THEME_SCRIPT, COMPILED_SCRIPT, THEME_FONT, LIBRARY_FONT):
            self.assertTrue(blocks(self.blocked, url), url)

    def test_theme_images_other_than_the_lcp_image_are_blocked(self):
        self.assertTrue(blocks(self.blocked, LOGO))

    def test_the_lcp_image_is_protected_at_every_width(self):
        self.assertEqual(self.protected, ["https://store.example/cdn/shop/files/image-31.png"])
        self.assertFalse(blocks(self.blocked, HERO))
        self.assertFalse(blocks(self.blocked, HERO_STUB))

    def test_stylesheets_apps_and_tags_stay(self):
        for url in (STYLESHEET, COMPILED_STYLESHEET, APP_SCRIPT, TAG_SCRIPT, PLATFORM_SCRIPT):
            self.assertFalse(blocks(self.blocked, url), url)

    def test_the_sample_is_taken_with_exactly_those_patterns(self):
        self.assertRegex(self.result.out, r"(?m)^SAMPLE s0006 ceiling home mobile control \| ")


class EachPageGetsItsOwnTarget(unittest.TestCase):
    """The real Ceiling Samples were taken with the patterns these baselines build.
    Their Performance scores, worked by hand:

        home        59 63 58 65 58  -> Ceiling 59
        collection  75 71 82 70 69  -> Ceiling 71
        product     68 59 64 65 66  -> Ceiling 65
    """

    def ceilings(self, *start_args):
        box = measured(self, *start_args)
        return [record(box, "ceiling", page, ceiling_reports(page)).lines("CEILING")[-1]
                for page in PAGES]

    def test_below_the_requested_score_each_target_is_the_pages_ceiling(self):
        self.assertEqual(self.ceilings(), [
            "CEILING home ceiling=59 requested=80 target=59",
            "CEILING collection ceiling=71 requested=80 target=71",
            "CEILING product ceiling=65 requested=80 target=65",
        ])

    def test_above_the_requested_score_the_target_is_the_requested_score(self):
        self.assertEqual(self.ceilings("--score", "65"), [
            "CEILING home ceiling=59 requested=65 target=59",
            "CEILING collection ceiling=71 requested=65 target=65",
            "CEILING product ceiling=65 requested=65 target=65",
        ])

    def test_status_keeps_every_target(self):
        box = measured(self)
        for page in PAGES:
            record(box, "ceiling", page, ceiling_reports(page))

        self.assertEqual(box.run("status").lines("CEILING"), [
            "CEILING home ceiling=59 requested=80 target=59",
            "CEILING collection ceiling=71 requested=80 target=71",
            "CEILING product ceiling=65 requested=80 target=65",
        ])


class ACeilingSampleIsChecked(unittest.TestCase):
    def setUp(self):
        self.box = measured(self)

    def variant(self, change):
        data = read_report("home-ceiling-1")
        change(data)
        path = self.box.root / "variant.json"
        path.write_text(json.dumps(data))
        return path

    def test_a_report_taken_with_other_patterns_is_rejected(self):
        fewer = self.variant(lambda r: r["configSettings"]["blockedUrlPatterns"].pop())

        result = self.box.run("ceiling", "--page", "home", "--report", fewer)

        self.assertEqual(result.code, 1, result)
        self.assertIn("SAMPLE rejected home mobile control: wrong-blocking 28 patterns, not 29",
                      result.lines("SAMPLE"))

    def test_a_report_whose_lcp_image_was_blocked_is_rejected(self):
        def block_the_hero(r):
            for item in r["audits"]["network-requests"]["details"]["items"]:
                if "/files/image-31.png" in item["url"]:
                    item["statusCode"] = -1
        blocked = self.variant(block_the_hero)

        result = self.box.run("ceiling", "--page", "home", "--report", blocked)

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^SAMPLE rejected home mobile control: lcp-blocked "
                                     r"https://store\.example/cdn/shop/files/image-31\.png\?")

    def test_a_ceiling_report_cannot_pass_as_a_baseline_sample(self):
        box, _, _ = started(self)

        result = box.run("sample", "--page", "home", "--device", "mobile",
                         "--report", report("home-ceiling-1"))

        self.assertEqual(result.lines("SAMPLE"),
                         ["SAMPLE rejected home mobile control: wrong-blocking 29 patterns, not 0"])


class AMovedLargestPaintIsSaid(unittest.TestCase):
    def test_a_lazy_loaded_lcp_image_that_never_loaded_makes_the_ceiling_a_rough_estimate(self):
        box = measured(self)

        result = record(box, "ceiling", "home", ceiling_reports("home"))

        self.assertRegex(result.out, r"(?m)^NOTE home: the LCP image loads only through a theme "
                                     r"script \(a lazy loader\), so with theme scripts blocked it "
                                     r"never loaded, and the largest paint moved to .* \(text\) in "
                                     r"5 of 5 Ceiling Samples\. ")


if __name__ == "__main__":
    unittest.main()
