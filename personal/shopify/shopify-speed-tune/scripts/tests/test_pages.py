"""The three pages: home, a collection from the main navigation, a best-selling product."""

import unittest

from support import HERE, Sandbox, report

STOREFRONT = HERE / "fixtures" / "storefront"


class ProposingThePages(unittest.TestCase):
    def test_the_first_navigation_collection_and_the_first_available_best_seller(self):
        box = Sandbox(self)
        box.start()
        box.edit_store(lambda s: s.update(pages={
            "/": str(STOREFRONT / "home.html"),
            "/collections/all?sort_by=best-selling": str(STOREFRONT / "best-selling.html"),
            "/products/sold-out-bestseller.js": str(STOREFRONT / "sold-out-bestseller.js"),
            "/products/example-product.js": str(STOREFRONT / "example-product.js"),
        }))

        result = box.run("pages")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("PAGE"), [
            "PAGE home https://store.example/",
            "PAGE collection https://store.example/collections/example-collection "
            "(first collection in the main navigation)",
            "PAGE product https://store.example/products/example-product "
            "(first available product in best-selling order)",
        ])


class SettingThePages(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox(self)
        self.box.start()
        self.box.run("pages", "--collection", "/collections/example-collection",
                     "--product", "/products/example-product")

    def test_every_page_gets_a_mobile_and_a_desktop_baseline_measurement(self):
        for page, device in (("collection", "mobile"), ("collection", "desktop"),
                             ("product", "mobile"), ("product", "desktop")):
            recorded = self.box.run("sample", "--page", page, "--device", device,
                                    "--report", report("%s-%s-1" % (page, device)))
            self.assertEqual(recorded.code, 0, recorded)

        self.assertEqual(self.box.run("status").lines("MEASUREMENT"), [
            "MEASUREMENT baseline home mobile control incomplete 0/5",
            "MEASUREMENT baseline home desktop control incomplete 0/5",
            "MEASUREMENT baseline collection mobile control incomplete 1/5",
            "MEASUREMENT baseline collection desktop control incomplete 1/5",
            "MEASUREMENT baseline product mobile control incomplete 1/5",
            "MEASUREMENT baseline product desktop control incomplete 1/5",
        ])

    def test_a_report_of_another_page_is_rejected(self):
        result = self.box.run("sample", "--page", "collection", "--device", "mobile",
                              "--report", report("product-mobile-1"))

        self.assertEqual(result.lines("SAMPLE"), [
            "SAMPLE rejected collection mobile control: wrong-page "
            "https://store.example/products/example-product"])

    def test_a_path_that_is_not_a_collection_is_refused(self):
        result = self.box.run("pages", "--collection", "/pages/about-us")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED bad-page: ")


if __name__ == "__main__":
    unittest.main()
