"""The guarded write: a Round's change reaches the Working theme, and only it.

Every theme write goes through the program, which pushes exactly the Round's
changed paths to one of the invocation's two unpublished themes, after reading
back from the store that it is still unpublished. The fake Shopify CLI keeps
each theme's files and answers a push the way CLI 4.8.2 does.
"""

import unittest

from round_support import CONTROL, EAGER, LAZY, THEME, WORKING, opened, write
from support import LIVE_THEME


class TheChangeReachesTheWorkingThemeOnly(unittest.TestCase):
    def setUp(self):
        self.box = opened(self)

    def test_a_pushed_change_reaches_the_working_theme_and_not_the_control_theme(self):
        write(self.box, "snippets/image.liquid", EAGER)

        result = self.box.run("push")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("PUSH"), ["PUSH working theme=%d paths=1 ok" % WORKING])
        self.assertEqual(self.box.theme_files(WORKING)["snippets/image.liquid"], EAGER)
        self.assertEqual(self.box.theme_files(CONTROL)["snippets/image.liquid"], LAZY)

    def test_a_deleted_file_leaves_the_working_theme_and_a_new_one_joins_it(self):
        (self.box.repo / "assets" / "slider.js").unlink()
        write(self.box, "snippets/hero-preload.liquid", "{{ image | image_url: width: 800 }}\n")
        before = self.box.theme_files(WORKING)

        result = self.box.run("push")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("CHANGE"), ["CHANGE D assets/slider.js",
                                                  "CHANGE A snippets/hero-preload.liquid"])
        after = self.box.theme_files(WORKING)
        self.assertNotIn("assets/slider.js", after)
        self.assertEqual(after["snippets/hero-preload.liquid"], "{{ image | image_url: width: 800 }}\n")
        untouched = {p: t for p, t in before.items() if p != "assets/slider.js"}
        self.assertEqual({p: t for p, t in after.items() if p in untouched}, untouched)
        self.assertIn("assets/slider.js", self.box.theme_files(CONTROL))

    def test_a_file_reverted_after_an_earlier_push_goes_back_on_the_next_push(self):
        write(self.box, "snippets/image.liquid", EAGER)
        write(self.box, "assets/theme.js", "/* first try */\n")
        self.box.run("push")
        write(self.box, "assets/theme.js", THEME["assets/theme.js"])

        result = self.box.run("push")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("CHANGE"), ["CHANGE M snippets/image.liquid"])
        self.assertEqual(self.box.theme_files(WORKING)["assets/theme.js"], THEME["assets/theme.js"])


# A comment the Shopify parser refuses although Theme Check passes it: the CLI's
# push reports it in its JSON and still exits 0.
MULTI_LINE_COMMENT = ("{%- # Load the hero eagerly:\n"
                      "     it is the LCP element -%}\n" + EAGER)


class APushThatReportsErrorsFailsTheRound(unittest.TestCase):
    def setUp(self):
        self.box = opened(self)

    def test_errors_in_the_push_json_fail_the_round(self):
        write(self.box, "snippets/image.liquid", MULTI_LINE_COMMENT)

        result = self.box.run("push")

        self.assertEqual(result.code, 1, result)
        self.assertEqual(result.lines("FAILED"), [
            "FAILED push-errors: the Working theme %d refused the change, so Round 1 failed"
            % WORKING])
        self.assertIn("NOTE snippets/image.liquid: Liquid syntax error (line 1): Syntax error in "
                      "tag '#' - Each line of comments must be prefixed by the '#' character",
                      result.out)
        self.assertEqual(result.lines("PUSH"), [])

    def test_a_warning_without_file_errors_fails_the_round_too(self):
        self.box.edit_store(lambda s: s.update(fails_without_detail=["snippets/image.liquid"]))
        write(self.box, "snippets/image.liquid", EAGER)

        result = self.box.run("push")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^FAILED push-errors: ")
        self.assertIn("NOTE [default] The theme 'speed-tune", result.out)

    def test_a_failed_round_takes_no_second_push(self):
        write(self.box, "snippets/image.liquid", MULTI_LINE_COMMENT)
        self.box.run("push")
        write(self.box, "snippets/image.liquid", EAGER)

        result = self.box.run("push")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED round-failed: Round 1 failed its push")
        self.assertEqual(len(self.box.pushes()), 1)


class AWriteToAnyOtherThemeIsRefused(unittest.TestCase):
    """Nothing is written when the guard refuses: the fake store records every push."""

    def setUp(self):
        self.box = opened(self)
        write(self.box, "snippets/image.liquid", EAGER)

    def refused(self, *args):
        result = self.box.run("push", *args)
        self.assertEqual(result.code, 1, result)
        self.assertEqual(self.box.pushes(), [], "the guard must refuse before any push")
        return result

    def test_the_published_themes_id_is_refused(self):
        result = self.refused("--theme", str(LIVE_THEME))

        self.assertEqual(result.lines("REFUSED"), [
            "REFUSED not-invocation-theme: %d is not one of this invocation's two themes "
            "(control %d, working %d)" % (LIVE_THEME, CONTROL, WORKING)])

    def test_another_unpublished_theme_is_refused(self):
        result = self.refused("--theme", "101")

        self.assertRegex(result.out, r"(?m)^REFUSED not-invocation-theme: 101 is not one of ")

    def test_the_control_theme_never_receives_a_change_under_test(self):
        result = self.refused("--theme", str(CONTROL))

        self.assertRegex(result.out, r"(?m)^REFUSED control-theme: ")

    def test_a_working_theme_that_was_published_is_refused(self):
        def publish_working(state):
            for theme in state["themes"]:
                if theme["id"] == LIVE_THEME:
                    theme["role"] = "unpublished"
                if theme["id"] == WORKING:
                    theme["role"] = "live"
        self.box.edit_store(publish_working)

        result = self.refused()

        self.assertEqual(result.lines("REFUSED"), [
            "REFUSED theme-published: the working theme %d is now the published theme" % WORKING])

    def test_a_working_theme_no_longer_in_the_library_is_refused(self):
        self.box.edit_store(lambda s: s.update(
            themes=[t for t in s["themes"] if t["id"] != WORKING]))

        result = self.refused()

        self.assertRegex(result.out, r"(?m)^REFUSED theme-missing: the working theme %d " % WORKING)


if __name__ == "__main__":
    unittest.main()
