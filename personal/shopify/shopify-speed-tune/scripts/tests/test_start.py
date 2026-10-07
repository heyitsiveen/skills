"""Starting an invocation: the store must be the repo's, and the machine must be free."""

import re
import unittest

from support import LIVE_THEME, STORE_URL, Sandbox


class StoreMustMatchTheRepo(unittest.TestCase):
    def test_a_store_that_is_not_the_repos_is_refused(self):
        box = Sandbox(self)
        box.edit_store(lambda s: s["shop"].update(myshopify_domain="other-store.myshopify.com"))

        result = box.run("start", "--store", STORE_URL)

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED store-mismatch: ")
        self.assertIn("other-store.myshopify.com", result.out)
        self.assertIn("example-store.myshopify.com", result.out)
        self.assertFalse(box.lock.exists(), "a refused start must not take the lock")
        self.assertEqual(box.theme_ids(), {LIVE_THEME, 101, 102})

    def test_the_matching_store_gets_an_unpublished_working_and_control_theme(self):
        box = Sandbox(self)

        themes, result = box.start()

        self.assertRegex(result.out, r"(?m)^START ready$")
        self.assertEqual(set(themes), {"working", "control"})
        self.assertNotEqual(themes["working"], themes["control"])
        library = {t["id"]: t for t in box.store()["themes"]}
        for theme_id in themes.values():
            self.assertEqual(library[theme_id]["role"], "unpublished")


class BothThemesMustPreview(unittest.TestCase):
    def test_a_store_that_refuses_to_share_a_preview_stops_start(self):
        box = Sandbox(self)
        box.edit_store(lambda s: s.update(refuses_sharing=True))

        result = box.run("start", "--store", STORE_URL)

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^FAILED preview-refused: ")
        self.assertNotIn("START ready", result.out)


class TheRepoMustNameOnlyItsStore(unittest.TestCase):
    def test_a_repo_without_shopify_theme_toml_is_refused(self):
        box = Sandbox(self)
        repo = box.root / "no-toml"
        box.make_repo(repo, toml="")
        (repo / "shopify.theme.toml").unlink()
        box.git(repo, "commit", "-qam", "drop toml")

        result = box.run("start", "--store", STORE_URL, cwd=repo)

        self.assertRegex(result.out, r"(?m)^REFUSED no-store-config: ")

    def test_a_toml_that_also_names_a_theme_is_refused(self):
        box = Sandbox(self)
        repo = box.make_repo(box.root / "pinned-theme", toml=(
            '[environments.default]\nstore = "example-store.myshopify.com"\ntheme = "100"\n'))

        result = box.run("start", "--store", STORE_URL, cwd=repo)

        self.assertRegex(result.out, r"(?m)^REFUSED store-config-has-more: .*\btheme\b")
        self.assertFalse(box.lock.exists())


class TheThemeLibraryMustHaveRoomForTwo(unittest.TestCase):
    def test_a_library_with_one_free_slot_is_refused_and_nothing_is_deleted(self):
        box = Sandbox(self)
        box.edit_store(lambda s: s["themes"].extend(
            {"id": 300 + i, "name": "Draft %d" % i, "role": "unpublished", "processing": False}
            for i in range(17)))  # 19 of 20 counted; the development theme is not
        themes_before = box.theme_ids()

        result = box.run("start", "--store", STORE_URL)

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED no-theme-room: .*19 of 20")
        self.assertEqual(box.theme_ids(), themes_before)

    def test_a_plus_store_may_say_its_limit_is_higher(self):
        box = Sandbox(self)
        box.edit_store(lambda s: s["themes"].extend(
            {"id": 300 + i, "name": "Draft %d" % i, "role": "unpublished", "processing": False}
            for i in range(17)))

        box.start("--theme-limit", "100")


class OneUnfinishedInvocationPerMachine(unittest.TestCase):
    def test_a_second_start_is_refused_while_the_first_is_unfinished(self):
        box = Sandbox(self)
        _, first = box.start()
        invocation = re.search(r"^START invocation=(\S+)", first.out, re.M).group(1)
        other_repo = box.make_repo(box.root / "other-client")
        themes_before = box.theme_ids()

        result = box.run("start", "--store", STORE_URL, cwd=other_repo)

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED invocation-unfinished: invocation %s "
                         % re.escape(invocation))
        self.assertEqual(box.theme_ids(), themes_before, "a refused start creates no theme")

    def test_unlock_naming_the_stale_invocation_frees_the_machine(self):
        box = Sandbox(self)
        _, first = box.start()
        invocation = re.search(r"^START invocation=(\S+)", first.out, re.M).group(1)
        other_repo = box.make_repo(box.root / "other-client")

        cleared = box.run("unlock", "--invocation", invocation, cwd=other_repo)

        self.assertEqual(cleared.code, 0, cleared)
        self.assertRegex(cleared.out, r"(?m)^UNLOCK released %s" % re.escape(invocation))
        box.start(cwd=other_repo)

    def test_unlock_naming_another_invocation_keeps_the_lock(self):
        box = Sandbox(self)
        box.start()

        cleared = box.run("unlock", "--invocation", "20000101-000000")

        self.assertEqual(cleared.code, 1, cleared)
        self.assertRegex(cleared.out, r"(?m)^REFUSED wrong-invocation: ")
        again = box.run("start", "--store", STORE_URL)
        self.assertRegex(again.out, r"(?m)^REFUSED invocation-unfinished: ")


if __name__ == "__main__":
    unittest.main()
