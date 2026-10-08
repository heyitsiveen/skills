"""The smoke check: the Working theme must still do what the Control theme does.

The results fixture is a real store's baseline smoke check: its three pages on
two duplicates of its published theme, with the store's identity replaced. The
store is store.example, and the themes are the sandbox's (Working 200, Control
201). Each app block id keeps its real shape, `shopify-block-<token>__<key>`,
with a neutral token and key: Shopify gives a section's app block a token of the
theme's own, so the same block has a different id on each duplicate, while an
app embed's id is the same on both. Each case is derived from it by editing the
one field that makes the case.
"""

import json
import os
import unittest

from support import LIVE_THEME, SMOKE_RESULTS, Sandbox

RESULTS = SMOKE_RESULTS


def results_file(box, change=None, name="smoke-results.json"):
    """The real results with one change, as a file the program can record."""
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    if change:
        change(data)
    path = box.root / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def opened_invocation(test):
    box = Sandbox(test)
    box.start()
    box.run("pages", "--collection", "/collections/example-collection",
            "--product", "/products/example-product")
    return box


class JudgingRecordedResults(unittest.TestCase):
    def setUp(self):
        self.box = opened_invocation(self)

    def record(self, change=None):
        return self.box.run("smoke", "--results", results_file(self.box, change))

    def test_checks_that_pass_on_both_themes_pass(self):
        result = self.record()

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("SMOKE")[-1], "SMOKE baseline result pass")

    def test_a_check_that_passes_on_the_control_theme_only_fails(self):
        result = self.record(lambda r: r["pages"]["product"]["working"]["checks"].update({
            "add-to-cart": {"status": "fail", "detail": "the cart still holds 0 item(s)"},
            "cart-count": {"status": "skip", "detail": "nothing was added"}}))

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("SMOKE")[-3:], [
            "SMOKE baseline product regression add-to-cart: control pass, working fail "
            "(the cart still holds 0 item(s))",
            "SMOKE baseline product regression cart-count: control pass, working skip "
            "(nothing was added)",
            "SMOKE baseline result fail: 2 regressions"])

    def test_a_check_that_fails_on_both_themes_is_not_held_against_the_working_theme(self):
        def variant_fails_on_both(r):
            for role in ("control", "working"):
                r["pages"]["product"][role]["checks"]["variant"] = {
                    "status": "fail", "detail": "no control offers Size \"4 pack\""}

        result = self.record(variant_fails_on_both)

        self.assertEqual(result.code, 0, result)
        self.assertNotIn("regression", result.out)
        self.assertIn("SMOKE baseline product working theme=200 | load pass | menu-open pass | "
                      "menu-close pass | variant fail | add-to-cart pass | cart-count pass | "
                      "app-blocks 3 | console-errors 0 | liquid-errors 0", result.lines("SMOKE"))
        self.assertEqual(result.lines("SMOKE")[-1], "SMOKE baseline result pass")

    def test_a_console_error_absent_on_the_control_theme_fails(self):
        result = self.record(lambda r: r["pages"]["home"]["working"]["console_errors"].append({
            "text": "Uncaught ReferenceError: Swiper is not defined",
            "url": "https://store.example/cdn/shop/t/24/assets/slider.js?v=172"}))

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("SMOKE")[-2:], [
            "SMOKE baseline home new-error console: Uncaught ReferenceError: Swiper is not defined "
            "(https://store.example/cdn/shop/t/24/assets/slider.js?v=172)",
            "SMOKE baseline result fail: 1 new error"])

    def test_an_error_that_differs_only_in_its_themes_asset_folder_is_not_new(self):
        def same_error_on_each_themes_own_assets(r):
            for role, number, version in (("control", 24, "172"), ("working", 23, "981")):
                r["pages"]["home"][role]["console_errors"].append({
                    "text": "Failed to load resource: the server responded with a status of 404 ()",
                    "url": "https://store.example/cdn/shop/t/%d/assets/slider.js?v=%s" % (number, version)})

        result = self.record(same_error_on_each_themes_own_assets)

        self.assertEqual(result.lines("SMOKE")[-1], "SMOKE baseline result pass")

    def test_liquid_error_text_absent_on_the_control_theme_fails(self):
        result = self.record(lambda r: r["pages"]["product"]["working"]["liquid_errors"].append(
            "Liquid error (sections/main-product line 214): Could not find asset snippets/price.liquid"))

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("SMOKE")[-2:], [
            "SMOKE baseline product new-error liquid: Liquid error (sections/main-product line 214): "
            "Could not find asset snippets/price.liquid",
            "SMOKE baseline result fail: 1 new error"])

    def test_a_liquid_error_the_change_only_moved_to_another_line_is_not_new(self):
        def moved(r):
            for role, line in (("control", 214), ("working", 230)):
                r["pages"]["product"][role]["liquid_errors"].append(
                    "Liquid error (sections/main-product line %d): Could not find asset "
                    "snippets/price.liquid" % line)

        result = self.record(moved)

        self.assertEqual(result.lines("SMOKE")[-1], "SMOKE baseline result pass")

    def test_a_page_that_no_longer_loads_on_the_working_theme_fails_all_it_had(self):
        def home_times_out(r):
            r["pages"]["home"]["working"].update(
                status=None, theme=None, served_by={}, app_blocks=[], console_errors=[],
                checks={"load": {"status": "fail",
                                 "detail": "did not load: Navigation timeout of 60000 ms exceeded"}})

        result = self.record(home_times_out)

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("SMOKE")[6:], [
            "SMOKE baseline home regression load: control pass, working fail "
            "(did not load: Navigation timeout of 60000 ms exceeded)",
            "SMOKE baseline home regression menu-open: control pass, working missing "
            "(the check did not run)",
            "SMOKE baseline home regression menu-close: control pass, working missing "
            "(the check did not run)",
            "SMOKE baseline home missing-app-block: "
            "shopify-block-AHomeControlTokenQ__example_feed_app_feed_block_Xk4Rq2",
            "SMOKE baseline home missing-app-block: shopify-block-AEmbedTokenNumber1__4100000000000000001",
            "SMOKE baseline home missing-app-block: shopify-block-AEmbedTokenNumber2__4100000000000000002",
            "SMOKE baseline result fail: 3 regressions, 3 missing app blocks"])

    def test_an_app_block_missing_on_the_working_theme_fails(self):
        result = self.record(lambda r: r["pages"]["product"]["working"]["app_blocks"].remove(
            "shopify-block-AProdWorkingTokenQ__example_restock_app_restock_form_Pz8Lm3"))

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("SMOKE")[-2:], [
            "SMOKE baseline product missing-app-block: "
            "shopify-block-AProdControlTokenQ__example_restock_app_restock_form_Pz8Lm3",
            "SMOKE baseline result fail: 1 missing app block"])

    def test_one_of_two_app_blocks_of_the_same_key_gone_from_the_working_theme_fails(self):
        def feed_twice_on_control_once_on_working(r):
            r["pages"]["home"]["control"]["app_blocks"].append(
                "shopify-block-AHomeControlTokenR__example_feed_app_feed_block_Xk4Rq2")

        result = self.record(feed_twice_on_control_once_on_working)

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("SMOKE")[-2:], [
            "SMOKE baseline home missing-app-block: "
            "shopify-block-AHomeControlTokenR__example_feed_app_feed_block_Xk4Rq2",
            "SMOKE baseline result fail: 1 missing app block"])


class RecordingResults(unittest.TestCase):
    def setUp(self):
        self.box = opened_invocation(self)

    def test_recorded_results_stay_in_the_ledger_under_their_label(self):
        self.box.run("smoke", "--label", "round-1", "--results", results_file(
            self.box, lambda r: r["pages"]["home"]["working"]["checks"].update({
                "menu-open": {"status": "fail", "detail": 'Enter on button "Open menu" opened no menu'},
                "menu-close": {"status": "skip", "detail": "the menu did not open"}})))

        status = self.box.run("status")

        self.assertIn("SMOKE round-1 result fail: 2 regressions", status.lines("SMOKE"))

    def test_status_judges_the_stored_results_by_the_rule_in_force_on_each_read(self):
        """The ledger keeps what the checker saw, never a verdict on it, so a result recorded
        under an earlier rule reads by today's."""
        self.box.run("smoke", "--results", results_file(self.box))

        self.assertEqual(self.box.run("status").lines("SMOKE"), ["SMOKE baseline result pass"])

    def test_a_label_holds_one_result_so_a_failed_check_cannot_be_retried_away(self):
        self.box.run("smoke", "--label", "round-1", "--results", results_file(
            self.box, lambda r: r["pages"]["product"]["working"]["app_blocks"].clear()))

        again = self.box.run("smoke", "--label", "round-1", "--results", results_file(self.box))

        self.assertEqual(again.code, 1, again)
        self.assertRegex(again.out, r"(?m)^REFUSED smoke-recorded: ")
        self.assertEqual(self.box.run("status").lines("SMOKE"),
                         ["SMOKE round-1 result fail: 3 missing app blocks"])

    def test_a_page_the_store_rendered_with_its_published_theme_is_refused(self):
        def published_theme_served(r):
            run = r["pages"]["collection"]["working"]
            run["theme"] = LIVE_THEME
            run["served_by"] = {str(LIVE_THEME): 1}

        result = self.box.run("smoke", "--results", results_file(self.box, published_theme_served))

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED smoke-wrong-theme: the collection page on the "
                                     r"working theme was rendered by theme 100, not 200")
        self.assertEqual(self.box.run("status").lines("SMOKE"), [])

    def test_a_later_request_the_store_rendered_with_another_theme_is_refused(self):
        result = self.box.run("smoke", "--results", results_file(
            self.box, lambda r: r["pages"]["product"]["control"]["served_by"].update(
                {str(LIVE_THEME): 1})))

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED smoke-wrong-theme: the product page on the "
                                     r"control theme was rendered by theme 100, not 201")

    def test_a_loaded_page_that_names_no_theme_is_refused(self):
        result = self.box.run("smoke", "--results", results_file(
            self.box, lambda r: r["pages"]["home"]["working"].update(theme=None, served_by={})))

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED smoke-wrong-theme: the home page on the "
                                     r"working theme loaded but named no theme")

    def test_results_of_another_page_or_url_are_refused(self):
        result = self.box.run("smoke", "--results", results_file(
            self.box, lambda r: r["pages"]["product"]["working"].update(
                url="https://store.example/products/example-product")))

        self.assertEqual(result.code, 1, result)
        self.assertIn("REFUSED smoke-wrong-page: the product page on the working theme was loaded "
                      "from https://store.example/products/example-product, not "
                      "https://store.example/products/example-product?pb=0", result.out)


class RunningTheChecker(unittest.TestCase):
    """The fake `node` stands in for the smoke checker: it answers with the real
    results, each page rendered by the theme whose preview cookie it was given,
    and only while the Chrome at its port is running."""

    def setUp(self):
        self.box = opened_invocation(self)

    def test_the_checker_compares_both_themes_in_the_invocations_chrome(self):
        result = self.box.run("smoke")

        self.assertEqual(result.code, 0, result)
        self.assertIn("SMOKE baseline product control theme=201 | load pass | menu-open pass | "
                      "menu-close pass | variant pass | add-to-cart pass | cart-count pass | "
                      "app-blocks 3 | console-errors 0 | liquid-errors 0", result.lines("SMOKE"))
        self.assertIn("SMOKE baseline product working theme=200 | load pass | menu-open pass | "
                      "menu-close pass | variant pass | add-to-cart pass | cart-count pass | "
                      "app-blocks 3 | console-errors 0 | liquid-errors 0", result.lines("SMOKE"))
        self.assertEqual(result.lines("SMOKE")[-1], "SMOKE baseline result pass")

    def test_its_chrome_is_stopped_and_the_preview_cookies_are_kept_nowhere(self):
        result = self.box.run("smoke")

        started = self.box.chromes_started()
        self.assertEqual(len(started), 1)
        self.assertFalse(os.path.exists(started[0]["profile"]))
        folder = self.box.repo / ".agent" / "shopify-speed-tune"
        kept = "".join(p.read_text() for p in folder.rglob("*") if p.is_file())
        workspace = "".join(p.read_text(errors="replace") for p in self.box.workspace().rglob("*")
                            if p.is_file() and p.suffix == ".json")
        for secret in self.box.secrets_seen():
            self.assertNotIn(secret, kept + workspace + result.out + result.err)

    def test_a_page_whose_preview_the_store_dropped_part_way_is_not_recorded(self):
        self.box.edit_store(lambda s: s.update(lost_cookie=["product", "working"]))

        result = self.box.run("smoke")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^FAILED smoke-wrong-theme: the product page on the "
                                     r"working theme was rendered by theme 100, not 200")
        self.assertEqual(self.box.run("status").lines("SMOKE"), [])


if __name__ == "__main__":
    unittest.main()
