"""What a Round's change may hold before it reaches a theme.

A change is theme code only. It never touches the merchant's theme settings
file, which going live would overwrite, and it never adds a way to tell
Lighthouse, its test phone or its platform from a visitor, which would fake the
score. A refused change writes nothing. Template JSON may change, and every
such change is flagged for the report.
"""

import json
import unittest

from round_support import THEME, approved, opened, write


class ARefusedChangeWritesNothing(unittest.TestCase):
    def setUp(self):
        self.box = opened(self)

    def push_refused(self):
        result = self.box.run("push")
        self.assertEqual(result.code, 1, result)
        self.assertEqual(self.box.pushes(), [], "a refused change must not reach any theme")
        return result

    def test_a_change_to_the_merchants_settings_file_is_refused(self):
        settings = json.loads(THEME["config/settings_data.json"])
        settings["current"]["preload_hero"] = True
        write(self.box, "config/settings_data.json", json.dumps(settings, indent=2) + "\n")

        result = self.push_refused()

        self.assertEqual(result.lines("REFUSED"), [
            "REFUSED settings-file: the change touches config/settings_data.json, the merchant's "
            "theme settings file"])

    def test_each_way_of_detecting_the_test_is_refused(self):
        added = [
            "if (navigator.userAgent.includes('Chrome-Lighthouse')) { skipApps(); }",
            "const slow = window.navigator['platform'] === 'Linux x86_64';",
            "if (/moto g power/i.test(ua)) return;",
            "const { userAgent } = navigator;",
            "var p = '\\x4c\\x69\\x6e\\x75\\x78\\x20\\x78\\x38\\x36\\x5f\\x36\\x34';",
            "if (navigator.webdriver) { document.documentElement.classList.add('bot'); }",
            "// keeps the hero light for PageSpeed",
            "window.isAuditBot = /HeadlessChrome/.test(ua);",
        ]
        for line in added:
            with self.subTest(line=line):
                write(self.box, "assets/theme.js", THEME["assets/theme.js"] + line + "\n")

                result = self.push_refused()

                self.assertRegex(result.out, r"(?m)^REFUSED detection: assets/theme\.js line 2 adds ")

    def test_detection_in_an_inline_script_of_a_liquid_file_is_refused(self):
        write(self.box, "snippets/image.liquid", THEME["snippets/image.liquid"] +
              "<script>if (navigator.userAgent.indexOf('Lighthouse') > -1) {}</script>\n")

        result = self.push_refused()

        self.assertRegex(result.out, r"(?m)^REFUSED detection: snippets/image\.liquid line 2 adds ")

    def test_a_file_outside_the_theme_is_refused(self):
        write(self.box, "package.json", '{"name": "theme"}\n')

        result = self.push_refused()

        self.assertEqual(result.lines("REFUSED"), [
            "REFUSED outside-theme: the change touches package.json, which is not theme code"])


class WhatAChangeMayDo(unittest.TestCase):
    def test_removing_code_that_reads_the_user_agent_is_allowed(self):
        box = opened(self)
        (box.repo / "assets" / "slider.js").unlink()

        result = box.run("push")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("CHANGE"), ["CHANGE D assets/slider.js"])

    def test_a_template_json_change_is_flagged_for_the_report(self):
        box = opened(self)
        index = json.loads(THEME["templates/index.json"])
        index["sections"]["hero"]["settings"] = {"image_loading": "eager"}
        write(box, "templates/index.json", json.dumps(index, indent=2) + "\n")

        result = box.run("push")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("CHANGE"), ["CHANGE M templates/index.json template-json"])
        self.assertIn("ROUND 1 open item=P1 pushed template-json=templates/index.json",
                      box.run("status").lines("ROUND"))

    def test_an_untracked_file_that_was_there_before_the_round_is_not_part_of_it(self):
        box = approved(self)
        write(box, "snippets/scratch.liquid", "{% comment %} the developer's own {% endcomment %}\n")
        box.run("round", "--item", "P1")
        write(box, "snippets/image.liquid", THEME["snippets/image.liquid"].replace("lazy", "eager"))

        result = box.run("push")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("CHANGE"), ["CHANGE M snippets/image.liquid"])


if __name__ == "__main__":
    unittest.main()
