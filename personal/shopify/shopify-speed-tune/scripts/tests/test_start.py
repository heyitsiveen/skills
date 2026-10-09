"""Starting an invocation: the store must be the repo's, the machine must be free, and
the repo's own pre-commit hook must pass, since every kept Round is committed through it."""

import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from support import (FAILING_HOOK, HOOK_ENDING, LIVE_THEME, STORE_URL, Sandbox, hook,
                     long_failing_hook, running)

# The REFUSED line for a hook that fails as FAILING_HOOK does.
HOOK_REFUSED = ("REFUSED pre-commit-fails: the pre-commit hook .git/hooks/pre-commit exits 1 on "
                "the unchanged repo: 412 files inspected with 733 total offenses found across "
                "120 files. | 12 errors. | 700 warnings. | 21 info issues. | husky - pre-commit "
                "script failed (code 1)")


def old_git_on_path(test):
    """A folder holding a git older than 2.36, which has no `git hook`; every other
    command goes to the real git."""
    folder = Path(tempfile.mkdtemp(prefix="speed-tune-old-git-"))
    test.addCleanup(shutil.rmtree, folder, True)
    stand_in = folder / "git"
    stand_in.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  --version) echo 'git version 2.30.2'; exit 0 ;;\n"
        "  hook) echo \"git: 'hook' is not a git command. See 'git --help'.\" >&2; exit 1 ;;\n"
        "esac\n"
        "exec '%s' \"$@\"\n" % shutil.which("git"))
    stand_in.chmod(0o755)
    return str(folder)


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

    def test_start_installs_puppeteer_core_for_the_browser_helpers_in_its_workspace(self):
        box = Sandbox(self)

        _, result = box.start()

        self.assertIn("START puppeteer-core=25.12.0", result.lines("START"))
        workspaces = [p for p in box.tmp.iterdir() if p.name.startswith("shopify-speed-tune-")]
        self.assertEqual(len(workspaces), 1)
        self.assertTrue((workspaces[0] / "node" / "node_modules" / "puppeteer-core").is_dir())


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


class TheReposPreCommitHookMustPass(unittest.TestCase):
    def test_a_hook_failing_on_the_unchanged_repo_refuses_before_anything_exists(self):
        box = Sandbox(self)
        hook(box.repo, FAILING_HOOK)

        result = box.run("start", "--store", STORE_URL)

        self.assertEqual(result.code, 1, result)
        self.assertEqual(result.lines("REFUSED"), [HOOK_REFUSED])
        self.assertFalse(box.lock.exists(), "a refused start must not take the lock")
        self.assertEqual(box.theme_ids(), {LIVE_THEME, 101, 102})
        self.assertEqual(box.git(box.repo, "branch", "--list", "speed-tune/*"), "")

    def test_the_hook_is_the_one_git_runs_through_core_hooks_path_as_husky_sets_it(self):
        box = Sandbox(self)
        hook(box.repo, "exit 0\n")  # .git/hooks, which git no longer reads once hooksPath is set
        hook(box.repo, 'sh -e "$(dirname "$0")/../pre-commit"\n', ".husky/_/pre-commit")
        (box.repo / ".husky" / "pre-commit").write_text(FAILING_HOOK)
        box.git(box.repo, "config", "core.hooksPath", ".husky/_")

        result = box.run("start", "--store", STORE_URL)

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^REFUSED pre-commit-fails: the pre-commit hook "
                                     r"\.husky/_/pre-commit exits 1 on the unchanged repo: ")

    def test_a_git_without_git_hook_run_gets_the_hook_file_run_from_the_repo_root(self):
        box = Sandbox(self)
        hook(box.repo, FAILING_HOOK)
        old_git = old_git_on_path(self)

        result = box.run("start", "--store", STORE_URL,
                         env={"PATH": old_git + os.pathsep + box.env()["PATH"]})

        self.assertEqual(result.lines("REFUSED"), [HOOK_REFUSED])

    def test_a_hook_writing_past_what_a_pipe_holds_keeps_its_summary(self):
        # The second real invocation lost theme check's summary so, and showed a cut line of
        # page HTML run into husky's line.
        box = Sandbox(self)
        long_failing_hook(box.repo, box.root)

        result = box.run("start", "--store", STORE_URL)

        self.assertEqual(result.lines("REFUSED"), [HOOK_REFUSED])

    def test_shows_the_last_lines_as_a_terminal_would_when_nothing_counts_problems(self):
        box = Sandbox(self)
        page_html = "0123456789abcdefghij" * 15
        hook(box.repo, "printf '[error]: LiquidHTMLSyntaxError\\n'\n"
                       "printf '12  %s\\n'\n"
                       "printf '\\342\\240\\213 Checking\\r\\033[32m\\342\\234\\224\\033[39m "
                       "Checked\\r\\n'\n"
                       "echo 'husky - pre-commit script failed (code 1)'\n"
                       "exit 1\n" % page_html)

        result = box.run("start", "--store", STORE_URL)

        self.assertEqual(result.lines("REFUSED"), [
            "REFUSED pre-commit-fails: the pre-commit hook .git/hooks/pre-commit exits 1 on the "
            "unchanged repo: 12 0123456789abcdefghij0123456789abcdefghij0123456789abcdefghij"
            "0123456789abcdefghij0123456789abcdefghij0123456789abcdefghij0123456789abcdefghij"
            "0123456789abcd... | ✔ Checked | husky - pre-commit script failed (code 1)"])

    def test_a_hook_that_does_not_finish_is_stopped_with_its_children_and_refused(self):
        box = Sandbox(self)
        # Past its first line the hook lets go of its output, as a detached child would.
        hook(box.repo, "echo 'Checking theme'\nexec >/dev/null 2>&1\nsleep 60 &\n"
                       "echo $! > ../hook-child\nwait\n")

        result = box.run("start", "--store", STORE_URL, env={"SPEED_TUNE_HOOK_SECONDS": "1"})

        self.assertEqual(result.lines("REFUSED"), [
            "REFUSED pre-commit-fails: the pre-commit hook .git/hooks/pre-commit did not finish "
            "within 1 s on the unchanged repo: Checking theme"])
        child = int((box.root / "hook-child").read_text())
        self.assertFalse(running(child), "the hook's own children must be stopped too")
        self.assertFalse(box.lock.exists())

    def test_a_passing_hook_is_run_and_recorded(self):
        box = Sandbox(self)
        ran = box.root / "hook-ran"
        hook(box.repo, "echo ran >> '%s'\n" % ran)

        _, result = box.start()

        self.assertIn("START hook=passed path=.git/hooks/pre-commit", result.lines("START"))
        self.assertEqual(ran.read_text(), "ran\n")
        self.assertIn("hook=passed", box.run("status").lines("INVOCATION")[0])

    def test_a_hook_git_would_not_run_counts_as_absent(self):
        box = Sandbox(self)
        hook(box.repo, FAILING_HOOK).chmod(0o644)  # not executable: git skips it

        _, result = box.start()

        self.assertIn("START hook=absent", result.lines("START"))
        self.assertIn("hook=absent", box.run("status").lines("INVOCATION")[0])


class TheDevelopersApprovalToCommitWithoutTheHook(unittest.TestCase):
    def test_lets_a_failing_hook_through_for_this_invocation(self):
        box = Sandbox(self)
        hook(box.repo, FAILING_HOOK)

        _, result = box.start("--no-verify-approved")

        self.assertIn("START hook=bypass-approved path=.git/hooks/pre-commit exit=1",
                      result.lines("START"))
        self.assertIn("NOTE kept Rounds are committed with --no-verify, as the developer approved "
                      "for this invocation", result.lines("NOTE"))
        self.assertIn("hook=bypass-approved", box.run("status").lines("INVOCATION")[0])

    def test_is_not_used_when_the_hook_passes(self):
        box = Sandbox(self)
        hook(box.repo, "exit 0\n")

        _, result = box.start("--no-verify-approved")

        self.assertIn("START hook=passed path=.git/hooks/pre-commit", result.lines("START"))
        self.assertIn("NOTE the pre-commit hook passes, so kept Rounds are committed through it "
                      "and --no-verify-approved goes unused", result.lines("NOTE"))


if __name__ == "__main__":
    unittest.main()
