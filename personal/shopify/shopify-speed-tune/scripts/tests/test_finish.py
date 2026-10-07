"""Finishing an invocation: only the Working theme and the branch remain."""

import unittest

from support import STORE_URL, Sandbox


class FinishLeavesOnlyTheWorkingThemeAndTheBranch(unittest.TestCase):
    def test_finish_deletes_the_control_theme_and_keeps_the_working_theme(self):
        box = Sandbox(self)
        themes, _ = box.start()

        result = box.run("finish")

        self.assertEqual(result.code, 0, result)
        self.assertRegex(result.out, r"(?m)^FINISH done ")
        library = box.theme_ids()
        self.assertNotIn(themes["control"], library)
        self.assertIn(themes["working"], library)

    def test_finish_removes_chrome_and_frees_the_machine(self):
        box = Sandbox(self)
        box.start()

        box.run("finish")

        leftovers = [p.name for p in box.tmp.iterdir() if p.name.startswith("shopify-speed-tune-")]
        self.assertEqual(leftovers, [], "the temp workspace holding Chrome must be gone")
        box.start()

    def test_finish_keeps_the_invocation_branch_and_returns_to_the_starting_branch(self):
        box = Sandbox(self)
        _, started = box.start()
        branch = [l.split("=", 1)[1] for l in started.lines("START") if l.startswith("START branch=")][0]

        box.run("finish")

        self.assertEqual(box.git(box.repo, "branch", "--show-current"), "main")
        self.assertEqual(box.git(box.repo, "branch", "--list", branch).strip(" *"), branch)


class FinishDiscardsAnInvocationThatStoppedInPreflight(unittest.TestCase):
    def test_a_start_that_fails_part_way_is_cleaned_up_by_finish_discard(self):
        box = Sandbox(self)
        box.edit_store(lambda s: s.update(duplicate_errors_after=1))
        themes_before = box.theme_ids()

        started = box.run("start", "--store", STORE_URL)

        self.assertEqual(started.code, 1, started)
        self.assertRegex(started.out, r"(?m)^FAILED duplicate-failed: .*Maximum number of themes")
        self.assertIn("NOTE Run `finish --discard` to remove what start created and release "
                      "the lock.", started.out)

        finished = box.run("finish", "--discard")

        self.assertEqual(finished.code, 0, finished)
        self.assertEqual(box.theme_ids(), themes_before)
        self.assertEqual(box.git(box.repo, "branch", "--list", "speed-tune/*"), "")
        self.assertEqual(box.git(box.repo, "branch", "--show-current"), "main")
        box.edit_store(lambda s: s.update(duplicate_errors_after=10 ** 6))
        box.start()


if __name__ == "__main__":
    unittest.main()
