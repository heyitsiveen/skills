"""What a verdict does to the repo and the two themes.

Keep: one Conventional Commit on the invocation's branch, with no AI
attribution, then the same state pushed to the Control theme, so the next Round
is measured against it. Remove: no commit, the working tree back at the last
commit, and the Working theme pushed back to it.
"""

import stat
import unittest

from round_support import (CONTROL, EAGER, ITEMS, LAZY, NEUTRAL, THEME, WIN_4, WORKING, apply_item,
                           approved, checked, measure, opened, pushed, write)
from support import FAILING_HOOK, HOOK_ENDING, built, long_failing_hook


def commits_since(box, rev):
    return box.git(box.repo, "rev-list", "--count", "%s..HEAD" % rev)


def base_of_round(box):
    return box.git(box.repo, "rev-parse", "HEAD")


class AKeptRound(unittest.TestCase):
    def setUp(self):
        # Each test reads the kept Round, on a copy of its own (support.built).
        def build(test):
            box = pushed(test)
            base = base_of_round(box)
            checked(box)
            measure(box, {"home": WIN_4})
            result = box.run("verdict")
            test.assertEqual(result.code, 0, result)
            return box, (base, result)

        self.box, (self.base, self.result) = built(self, "kept-round", build)

    def test_makes_exactly_one_conventional_commit_without_ai_attribution(self):
        self.assertEqual(commits_since(self.box, self.base), "1")
        subject = self.box.git(self.box.repo, "log", "-1", "--format=%s")
        message = self.box.git(self.box.repo, "log", "-1", "--format=%B")
        self.assertEqual(subject, "perf(home): load the hero image eagerly")
        for attribution in ("Co-Authored-By", "Claude", "Anthropic", "AI", "Generated"):
            self.assertNotIn(attribution, message)
        self.assertEqual(self.box.git(self.box.repo, "show", "--name-only", "--format=", "HEAD"),
                         "snippets/image.liquid")

    def test_brings_the_control_theme_up_to_date(self):
        self.assertEqual(self.box.theme_files(CONTROL)["snippets/image.liquid"], EAGER)
        self.assertEqual(self.box.theme_files(WORKING)["snippets/image.liquid"], EAGER)
        self.assertEqual(self.box.theme_files(CONTROL), self.box.theme_files(WORKING))

    def test_says_so_on_its_lines_and_leaves_a_clean_tree(self):
        commit = self.box.git(self.box.repo, "rev-parse", "HEAD")
        self.assertIn("PUSH control theme=%d paths=1 ok" % CONTROL, self.result.lines("PUSH"))
        self.assertIn("ROUND 1 kept commit=%s" % commit[:12], self.result.lines("ROUND"))
        self.assertEqual(self.box.git(self.box.repo, "status", "--porcelain"), "")

    def test_closes_the_round_so_the_next_one_can_open(self):
        result = self.box.run("round")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("ROUND"), ["ROUND 2 opened item=P2 pages=home,collection,product"])


class ARemovedRound(unittest.TestCase):
    def setUp(self):
        # Each test reads the removed Round, on a copy of its own (support.built).
        def build(test):
            box = opened(test)
            base = base_of_round(box)
            write(box, "snippets/image.liquid", EAGER)
            (box.repo / "assets" / "slider.js").unlink()
            write(box, "snippets/hero-preload.liquid", "{{ image | image_url: width: 800 }}\n")
            test.assertEqual(box.run("push").code, 0)
            checked(box)
            measure(box, {"home": NEUTRAL})
            result = box.run("verdict")
            test.assertEqual(result.code, 0, result)
            return box, (base, result)

        self.box, (self.base, self.result) = built(self, "removed-round", build)

    def test_makes_no_commit_and_restores_the_working_tree(self):
        self.assertEqual(self.result.lines("VERDICT"), ["VERDICT 1 remove item=P1 reasons=no-win"])
        self.assertEqual(commits_since(self.box, self.base), "0")
        self.assertEqual(self.box.git(self.box.repo, "status", "--porcelain"), "")
        self.assertEqual((self.box.repo / "snippets" / "image.liquid").read_text(), LAZY)
        self.assertEqual((self.box.repo / "assets" / "slider.js").read_text(), THEME["assets/slider.js"])
        self.assertFalse((self.box.repo / "snippets" / "hero-preload.liquid").exists())

    def test_pushes_the_working_theme_back_to_the_last_commit(self):
        self.assertEqual(self.box.theme_files(WORKING), self.box.theme_files(CONTROL))
        self.assertEqual(self.box.theme_files(WORKING)["snippets/image.liquid"], LAZY)
        self.assertIn("PUSH working theme=%d paths=3 ok" % WORKING, self.result.lines("PUSH"))
        self.assertIn("ROUND 1 removed", self.result.lines("ROUND"))


class ARoundThatCannotBeMeasured(unittest.TestCase):
    def test_a_round_whose_push_failed_is_removed(self):
        box = opened(self)
        write(box, "snippets/image.liquid", "{%- # eager:\n     the LCP -%}\n" + EAGER)
        box.run("push")

        result = box.run("verdict")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("VERDICT"), ["VERDICT 1 remove item=P1 reasons=push-errors"])
        self.assertEqual((box.repo / "snippets" / "image.liquid").read_text(), LAZY)
        self.assertEqual(box.theme_files(WORKING), box.theme_files(CONTROL))

    def test_a_round_never_pushed_is_refused_a_verdict_unless_removal_is_asked_for(self):
        box = opened(self)
        write(box, "snippets/image.liquid", EAGER)

        refused = box.run("verdict")

        self.assertEqual(refused.code, 1, refused)
        self.assertRegex(refused.out, r"(?m)^REFUSED round-not-pushed: ")

        removed = box.run("verdict", "--remove")

        self.assertEqual(removed.code, 0, removed)
        self.assertEqual(removed.lines("VERDICT"), ["VERDICT 1 remove item=P1 reasons=not-pushed"])
        self.assertEqual((box.repo / "snippets" / "image.liquid").read_text(), LAZY)
        self.assertEqual(box.pushes(), [], "nothing reached a theme, so nothing is pushed back")


class TheRoundsRepoStaysWhereTheRoundLeftIt(unittest.TestCase):
    def test_a_commit_made_during_a_round_stops_its_push(self):
        box = opened(self)
        write(box, "snippets/image.liquid", EAGER)
        box.git(box.repo, "commit", "-qam", "eager hero")

        result = box.run("push")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED head-moved: ")
        self.assertEqual(box.pushes(), [])

    def test_the_change_cannot_be_pushed_again_once_its_smoke_check_ran(self):
        box = pushed(self)
        checked(box)
        write(box, "assets/theme.js", "/* one more thing */\n")

        result = box.run("push")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED round-measured: ")

    def test_a_tree_changed_after_the_push_is_removed_not_kept(self):
        box = pushed(self)
        checked(box)
        measure(box, {"home": WIN_4})
        write(box, "assets/theme.js", "/* changed after the pairs */\n")

        result = box.run("verdict")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("VERDICT"),
                         ["VERDICT 1 remove item=P1 reasons=changed-since-push"])
        self.assertEqual((box.repo / "assets" / "theme.js").read_text(), THEME["assets/theme.js"])
        self.assertEqual(box.theme_files(WORKING), box.theme_files(CONTROL))

    def test_finish_waits_for_the_open_round(self):
        box = pushed(self)

        result = box.run("finish")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED round-open: ")
        self.assertIn(CONTROL, box.theme_ids(), "nothing was cleaned up yet")


class TheReposOwnCommitHook(unittest.TestCase):
    """A keep commit runs the client repo's hooks, as the developer's own commits do."""

    def hook(self, box, script):
        path = box.repo / ".git" / "hooks" / "pre-commit"
        path.write_text("#!/bin/sh\n" + script)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def test_a_change_the_hook_refuses_is_removed(self):
        box = pushed(self)
        base = base_of_round(box)
        checked(box)
        measure(box, {"home": WIN_4})
        self.hook(box, "echo 'theme check: 1 offense' >&2\nexit 1\n")

        result = box.run("verdict")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("VERDICT"),
                         ["VERDICT 1 remove item=P1 reasons=commit-refused"])
        self.assertIn("NOTE theme check: 1 offense", result.out)
        self.assertEqual(commits_since(box, base), "0")
        self.assertEqual(box.theme_files(WORKING), box.theme_files(CONTROL))

    def test_a_refusal_shows_how_the_hook_ended_as_start_shows_it(self):
        box = pushed(self)
        checked(box)
        measure(box, {"home": WIN_4})
        long_failing_hook(box.repo, box.root)

        result = box.run("verdict")

        self.assertEqual(result.code, 0, result.lines("FAILED") or result.err[-2000:])
        self.assertEqual(result.lines("VERDICT"),
                         ["VERDICT 1 remove item=P1 reasons=commit-refused"])
        self.assertEqual(result.lines("NOTE"), ["NOTE " + line for line in HOOK_ENDING])

    def test_a_file_the_hook_reformats_reaches_both_themes_as_committed(self):
        box = pushed(self)
        checked(box)
        measure(box, {"home": WIN_4})
        # A formatter run by the hook, like lint-staged's prettier: rewrite, re-stage.
        self.hook(box, "printf '%s' \"$(cat snippets/image.liquid)\" > snippets/image.liquid\n"
                       "git add snippets/image.liquid\n")

        result = box.run("verdict")

        self.assertEqual(result.code, 0, result)
        committed = box.git(box.repo, "show", "HEAD:snippets/image.liquid")
        self.assertEqual(committed, EAGER.rstrip("\n"))
        self.assertEqual(box.theme_files(CONTROL)["snippets/image.liquid"], committed)
        self.assertEqual(box.theme_files(WORKING)["snippets/image.liquid"], committed)

    def test_a_failing_hook_the_developer_approved_bypassing_does_not_refuse_the_keep(self):
        box = approved(self, ITEMS, "--no-verify-approved", pre_commit=FAILING_HOOK)
        self.assertEqual(box.run("round", "--item", "P1").code, 0)
        base = base_of_round(box)
        apply_item(box, "P1")
        self.assertEqual(box.run("push").code, 0)
        checked(box)
        measure(box, {"home": WIN_4})

        result = box.run("verdict")

        self.assertEqual(result.lines("VERDICT"), ["VERDICT 1 keep item=P1 won=home"])
        self.assertEqual(commits_since(box, base), "1")
        self.assertEqual(box.theme_files(CONTROL), box.theme_files(WORKING))


if __name__ == "__main__":
    unittest.main()
