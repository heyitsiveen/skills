"""Known Golden theme defects: found by their detection rules, or not at all off Golden.

The theme files are plan_support's small stand-ins, written for these tests. The
pages' evidence comes from the real baseline reports, whose LCP image is a
lazysizes placeholder on all three pages.
"""

import unittest

from plan_support import DEFECTIVE, FIXED, measured, schema
from support import HERE

REFERENCE = HERE.parent.parent / "references" / "known-defects.md"


class AStoreNotOnGolden(unittest.TestCase):
    def test_finds_no_defects_and_carries_on(self):
        box = measured(self, theme_files={"config/settings_schema.json": schema("Dawn", "15.4.0")})

        result = box.run("diagnose")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("DEFECT"),
                         ['DEFECT none: the theme is "Dawn" 15.4.0, not Golden'])
        self.assertNotEqual(result.lines("COST"), [])


class AGoldenStore(unittest.TestCase):
    def test_every_known_defect_is_found_by_its_rule(self):
        box = measured(self, theme_files=DEFECTIVE)

        result = box.run("diagnose")

        self.assertEqual(result.code, 0, result)
        defects = result.lines("DEFECT")
        self.assertEqual(defects[0], "DEFECT theme Golden 3.0")
        self.assertEqual([d.split(":")[0] for d in defects[1:]], [
            "DEFECT D1 found", "DEFECT D2 found on home, collection, product",
            "DEFECT D3 found", "DEFECT D4 found"])

    def test_fixed_code_is_clear_even_beside_a_commented_out_old_copy(self):
        box = measured(self, theme_files=FIXED)

        defects = box.run("diagnose").lines("DEFECT")

        self.assertIn("DEFECT D1 clear", defects)
        self.assertIn("DEFECT D3 clear", defects)
        self.assertIn("DEFECT D4 clear", defects)

    def test_a_page_whose_lcp_image_waits_for_lazysizes_still_shows_d2(self):
        box = measured(self, theme_files=FIXED)

        defects = box.run("diagnose").lines("DEFECT")

        self.assertTrue(any(d.startswith("DEFECT D2 found on home, collection, product: ")
                            for d in defects), defects)


class AFixUpstream(unittest.TestCase):
    """The reference records the first Golden version that carries a fix; a store
    on that version or later skips the entry's check."""

    def reference_with_d4_fixed_in(self, box, version):
        copy = box.root / "known-defects.md"
        text = REFERENCE.read_text()
        start = text.index("## D4.")
        head, tail = text[:start], text[start:]
        copy.write_text(head + tail.replace("**Fixed in Golden:** not yet",
                                            "**Fixed in Golden:** %s" % version, 1))
        return copy

    def test_a_store_on_the_fixing_version_skips_that_check(self):
        files = dict(DEFECTIVE, **{"config/settings_schema.json": schema("Golden", "3.10")})
        box = measured(self, theme_files=files)
        reference = self.reference_with_d4_fixed_in(box, "3.2")

        result = box.run("diagnose", env={"SPEED_TUNE_KNOWN_DEFECTS": str(reference)})

        defects = result.lines("DEFECT")
        self.assertIn("DEFECT D4 skipped: fixed in Golden 3.2, and this theme is 3.10", defects)
        self.assertIn("DEFECT D1 found", [d.split(":")[0] for d in defects])

    def test_an_older_store_still_runs_the_check(self):
        box = measured(self, theme_files=DEFECTIVE)
        reference = self.reference_with_d4_fixed_in(box, "3.2")

        defects = box.run("diagnose", env={"SPEED_TUNE_KNOWN_DEFECTS": str(reference)}).lines("DEFECT")

        self.assertIn("DEFECT D4 found", [d.split(":")[0] for d in defects])


if __name__ == "__main__":
    unittest.main()
