"""How this store goes live and how it goes back, as the report tells the team.

Shopify's GitHub integration commits the merchant's admin edits to the
connected branch as shopify[bot], each titled after the connected theme
(`<repo>/<branch>`). A store whose published theme those commits name is
GitHub-connected; one with no such commit and no CI workflow that deploys
themes is CLI-managed. Anything else is not recognised: the report names what
it found and gives no steps.

The fake store's published theme is #100, named `example/main`; the Working
theme is #200.
"""

import re
import subprocess
import unittest
from pathlib import Path

from report_support import ran

BOT = {"GIT_AUTHOR_NAME": "shopify[bot]",
       "GIT_AUTHOR_EMAIL": "79544226+shopify[bot]@users.noreply.github.com",
       "GIT_COMMITTER_NAME": "GitHub", "GIT_COMMITTER_EMAIL": "noreply@github.com"}


def bot_commit(box, theme_name, ref="main"):
    """A commit Shopify's GitHub integration made on `ref` for the merchant's edits."""
    tree = box.git(box.repo, "rev-parse", ref + "^{tree}")
    sha = subprocess.run(["git", "commit-tree", tree, "-p", ref,
                          "-m", "Update from Shopify for theme %s" % theme_name,
                          "-m", "Committed from shop: Example store"],
                         cwd=box.repo, env=dict(box.env(), **BOT), check=True,
                         capture_output=True, text=True).stdout.strip()
    box.git(box.repo, "update-ref", "refs/heads/" + ref, sha)


def rename_live_theme(box, name):
    box.edit_store(lambda s: next(t for t in s["themes"] if t["role"] == "live").update(name=name))


def golive(test, box):
    result = box.run("report")
    test.assertEqual(result.code, 0, result)
    text = Path(re.search(r"(?m)^REPORT file (\S+)$", result.out).group(1)).read_text()
    found = text.split("### Going live and going back\n", 1)[1]
    return result, found.split("\n### ", 1)[0].split("\n## ", 1)[0]


def setup_line(result):
    return [l for l in result.lines("REPORT") if l.startswith("REPORT setup ")]


class AGitHubConnectedStore(unittest.TestCase):
    def setUp(self):
        self.box = ran(self, "reached")
        bot_commit(self.box, "example/main")
        self.result, self.text = golive(self, self.box)

    def test_is_recognised_by_shopifys_commits_naming_the_published_theme(self):
        self.assertEqual(setup_line(self.result), ["REPORT setup github-connected branch=main"])
        self.assertIn("**This store is GitHub-connected.**", self.text)

    def test_goes_live_by_merging_the_branch_into_the_connected_branch(self):
        self.assertRegex(self.text, r"1\. Merge the branch `speed-tune/[\d-]+` into `main` and "
                                    r"push `main`\.")
        self.assertIn("Leave the Working theme `speed-tune", self.text)
        self.assertIn("(#200) unpublished", self.text)

    def test_goes_back_by_reverting_the_merge(self):
        self.assertIn("To go back, revert the merge on `main` (`git revert -m 1 <merge commit>`) "
                      "and push `main`", self.text)


class ACliManagedStore(unittest.TestCase):
    def setUp(self):
        self.box = ran(self, "reached")
        rename_live_theme(self.box, "Example live")
        self.result, self.text = golive(self, self.box)

    def test_is_recognised_by_having_no_sign_of_a_deploy(self):
        self.assertEqual(setup_line(self.result), ["REPORT setup cli-managed"])
        self.assertIn("**This store is CLI-managed.**", self.text)

    def test_goes_live_by_bringing_over_the_merchants_edits_then_publishing_the_working_theme(self):
        self.assertIn("`config/settings_data.json`, `templates/*.json` and `sections/*.json`",
                      self.text)
        self.assertIn("`shopify theme publish --theme 200 --store example-store.myshopify.com`",
                      self.text)
        self.assertLess(self.text.index("settings_data.json"), self.text.index("theme publish"))

    def test_goes_back_by_publishing_the_previous_theme_again(self):
        self.assertIn("To go back, publish `Example live` (#100) again", self.text)


class AStoreNotRecognised(unittest.TestCase):
    def setUp(self):
        self.box = ran(self, "reached")

    def assert_no_steps(self, text):
        self.assertIn("**This store's setup was not recognised**", text)
        self.assertNotIn("To go live", text)
        self.assertNotIn("To go back", text)

    def test_one_deployed_by_a_ci_workflow_names_the_workflow(self):
        rename_live_theme(self.box, "Example live")
        workflow = self.box.repo / ".github" / "workflows" / "deploy.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("on: push\njobs:\n  deploy:\n    steps:\n"
                            "      - run: shopify theme push --live --path theme\n")

        result, text = golive(self, self.box)

        self.assertEqual(setup_line(result), ["REPORT setup not-recognised"])
        self.assert_no_steps(text)
        self.assertIn("`.github/workflows/deploy.yml`", text)

    def test_one_whose_shopify_commits_name_another_theme_names_both(self):
        bot_commit(self.box, "example/staging")

        result, text = golive(self, self.box)

        self.assertEqual(setup_line(result), ["REPORT setup not-recognised"])
        self.assert_no_steps(text)
        self.assertIn("`example/staging`", text)
        self.assertIn("`example/main`", text)

    def test_one_whose_published_theme_is_named_like_a_connected_theme_says_so(self):
        result, text = golive(self, self.box)

        self.assertEqual(setup_line(result), ["REPORT setup not-recognised"])
        self.assert_no_steps(text)
        self.assertIn("named `example/main`, the way Shopify's GitHub integration names", text)


class NothingToPublish(unittest.TestCase):
    def test_when_no_round_was_kept_there_are_no_steps(self):
        box = ran(self, "none-kept")
        rename_live_theme(box, "Example live")

        result, text = golive(self, box)

        self.assertEqual(setup_line(result), ["REPORT setup cli-managed"])
        self.assertIn("No Round was kept, so there is nothing to publish", text)
        self.assertNotIn("To go live", text)


class ThePublishedThemeChangedDuringTheInvocation(unittest.TestCase):
    def test_the_report_warns_before_any_step(self):
        box = ran(self, "reached")

        def swap(state):
            for theme in state["themes"]:
                if theme["id"] in (100, 101):
                    theme["role"] = "live" if theme["id"] == 101 else "unpublished"
        box.edit_store(swap)

        result, text = golive(self, box)

        self.assertRegex(result.out, r"(?m)^WARN live-theme-changed: ")
        self.assertIn("**The published theme changed during this invocation.**", text)
        self.assertIn("`Old draft` (#101)", text)


if __name__ == "__main__":
    unittest.main()
