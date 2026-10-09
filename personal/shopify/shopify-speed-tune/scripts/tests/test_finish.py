"""Finishing an invocation: only the Working theme and the branch remain.

`finish` does not take its own word for it: it reads back the theme library,
the repo and the machine, and says `FINISH done` only when the Control theme
is gone, the Working theme is still there, no Chrome or anything else runs from
the invocation's workspace, the workspace is gone, and the lock is free.
"""

import plistlib
import re
import subprocess
import sys
import time
import unittest

from report_support import ran
from round_support import CONTROL, WORKING, pushed
from support import PROGRAM, STORE_URL, Sandbox, built, running, started


class FinishLeavesOnlyTheWorkingThemeAndTheBranch(unittest.TestCase):
    def test_finish_deletes_the_control_theme_and_keeps_the_working_theme(self):
        box, themes, _ = started(self)

        result = box.run("finish")

        self.assertEqual(result.code, 0, result)
        self.assertRegex(result.out, r"(?m)^FINISH done ")
        library = box.theme_ids()
        self.assertNotIn(themes["control"], library)
        self.assertIn(themes["working"], library)

    def test_finish_removes_chrome_and_frees_the_machine(self):
        box, _, _ = started(self)

        box.run("finish")

        leftovers = [p.name for p in box.tmp.iterdir() if p.name.startswith("shopify-speed-tune-")]
        self.assertEqual(leftovers, [], "the temp workspace holding Chrome must be gone")
        box.start()

    def test_finish_keeps_the_invocation_branch_and_returns_to_the_starting_branch(self):
        box, _, opened = started(self)
        branch = [l.split("=", 1)[1] for l in opened.lines("START") if l.startswith("START branch=")][0]

        box.run("finish")

        self.assertEqual(box.git(box.repo, "branch", "--show-current"), "main")
        self.assertEqual(box.git(box.repo, "branch", "--list", branch).strip(" *"), branch)


class FinishLeavesTheDevelopersWorkAsItIs(unittest.TestCase):
    """finish puts the repo back on the branch it started from only when that loses nothing."""

    def test_a_switch_git_refuses_leaves_the_repo_on_the_invocations_branch_and_says_so(self):
        box = ran(self, "reached")  # P2 kept: its commit deleted assets/slider.js
        branch = box.git(box.repo, "branch", "--show-current")
        rebuilt = "// rebuilt by the developer's bundler\n"
        (box.repo / "assets" / "slider.js").write_text(rebuilt)

        result = box.run("finish")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(box.git(box.repo, "branch", "--show-current"), branch)
        self.assertEqual((box.repo / "assets" / "slider.js").read_text(), rebuilt)
        self.assertIn("FINISH branch kept %s (repo on %s)" % (branch, branch),
                      result.lines("FINISH"))
        self.assertRegex(result.out, r"(?m)^NOTE git did not switch the repo back to main, so it "
                                     r"stays on %s: error: The following untracked working tree "
                                     r"files would be overwritten by checkout" % re.escape(branch))


class FinishReadsBackWhatItLeaves(unittest.TestCase):
    def setUp(self):
        # Every test here only reads what `finish` printed.
        def build(test):
            box, themes, opened = started(test)
            branch = re.search(r"(?m)^START branch=(\S+)", opened.out).group(1)
            result = box.run("finish")
            test.assertEqual(result.code, 0, result)
            return box, (themes, branch, result)

        self.box, (self.themes, self.branch, self.result) = built(self, "finished", build)

    def test_from_the_theme_library_the_repo_and_the_machine_before_it_says_done(self):
        self.assertEqual(self.result.lines("FINISH")[-5:], [
            "FINISH verified themes control=gone working=unpublished",
            "FINISH verified branch=%s repo-on=main" % self.branch,
            "FINISH verified chrome=none workspace=gone awake=stopped preferences=as-before",
            "FINISH lock released",
            "FINISH done invocation=%s" % self.branch.split("/", 1)[1],
        ])

    def test_says_when_no_report_was_written(self):
        self.assertIn("NOTE no report was written: `report --invocation %s` writes it from the "
                      "ledger" % self.branch.split("/", 1)[1], self.result.out)


CFT_DOMAIN = "com.google.chrome.for.testing"


def domain_file(box):
    """Chrome for Testing's preferences domain, as the fake `defaults` keeps it."""
    folder = box.root / "defaults"
    folder.mkdir(exist_ok=True)
    return folder / (CFT_DOMAIN + ".plist")


def chrome_records_itself(box):
    """What Chrome for Testing does on every launch: it records where it ran from."""
    app = box.workspace() / "chrome" / "Google Chrome for Testing.app"
    domain_file(box).write_bytes(plistlib.dumps({"LastRunAppBundlePath": str(app)}))


class FinishPutsChromeForTestingsPreferencesBack(unittest.TestCase):
    BEFORE = {"LastRunAppBundlePath": "/Users/dev/old-checker/Google Chrome for Testing.app"}

    def test_and_reads_them_back_as_they_were_before_the_invocation(self):
        box = Sandbox(self)
        domain_file(box).write_bytes(plistlib.dumps(self.BEFORE))
        box.start()
        chrome_records_itself(box)

        result = box.run("finish")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(plistlib.loads(domain_file(box).read_bytes()), self.BEFORE)
        self.assertIn("FINISH verified chrome=none workspace=gone awake=stopped "
                      "preferences=as-before", result.lines("FINISH"))

    def test_a_restore_defaults_refuses_keeps_the_invocation_open(self):
        box, _, _ = started(self)
        chrome_records_itself(box)
        box.edit_store(lambda s: s.update(defaults_fails=["delete"]))

        result = box.run("finish")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^FAILED cleanup-incomplete: Chrome for Testing's "
                                     r"preferences were not put back: `defaults delete "
                                     r"com\.google\.chrome\.for\.testing` exited 1")
        self.assertEqual(box.run("status").code, 0, "the lock and the ledger stay open")

        box.edit_store(lambda s: s.update(defaults_fails=[]))
        again = box.run("finish")

        self.assertEqual(again.code, 0, again)
        self.assertFalse(domain_file(box).exists(), "the domain did not exist before the invocation")

    def test_a_restore_that_changed_nothing_is_caught_by_the_read_back(self):
        box = Sandbox(self)
        domain_file(box).write_bytes(plistlib.dumps(self.BEFORE))
        box.start()
        chrome_records_itself(box)
        box.edit_store(lambda s: s.update(defaults_ignores=["import"]))

        result = box.run("finish")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^FAILED cleanup-incomplete: Chrome for Testing's "
                                     r"preferences were not put back: they still differ from "
                                     r"before the invocation")
        self.assertEqual(box.run("status").code, 0, "the lock and the ledger stay open")


class FinishStopsTheChromeOfAJobCutOffPartWay(unittest.TestCase):
    def test_a_sample_killed_mid_run_leaves_a_chrome_that_finish_stops(self):
        box, _, _ = started(self)
        box.edit_store(lambda s: s["lighthouse"].update(hang=True))
        program = subprocess.Popen(
            [sys.executable, str(PROGRAM), "sample", "--page", "home", "--device", "mobile",
             "--count", "1"], cwd=box.repo, env=box.env(), stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        chrome = self.wait_for_chrome(box)
        program.kill()
        program.wait()
        self.assertTrue(running(chrome["pid"]), "the cut-off Sample's Chrome runs on")

        result = box.run("finish")

        self.assertEqual(result.code, 0, result)
        self.assertIn("FINISH chrome stopped pid=%d" % chrome["pid"], "\n".join(result.lines("FINISH")))
        self.assertFalse(running(chrome["pid"]))
        self.assertRegex(result.out, r"(?m)^FINISH done ")

    def wait_for_chrome(self, box):
        """The Sample's Chrome, once the preview cookie is in its jar and Lighthouse runs."""
        lighthouse = "--output-path=%s" % box.workspace()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            chromes = box.chromes_started()
            if chromes and (box.root / "chromes" / ("%s.jar" % self.port(box, chromes[0]))).exists() \
                    and lighthouse in subprocess.run(["ps", "-A", "-ww", "-o", "command="],
                                                     capture_output=True, text=True).stdout:
                return chromes[0]
            time.sleep(0.05)
        self.fail("the Sample never started its Chrome and Lighthouse")

    @staticmethod
    def port(box, chrome):
        return next(p.name for p in (box.root / "chromes").iterdir()
                    if p.name.isdigit() and str(chrome["pid"]) in p.read_text())


class FinishIsNotDoneWhileSomethingRemains(unittest.TestCase):
    def test_a_process_still_running_from_the_workspace_keeps_the_invocation_open(self):
        box, _, _ = started(self)
        stray = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)",
                                  str(box.workspace() / "stray")])
        self.addCleanup(stray.wait)
        self.addCleanup(stray.kill)

        result = box.run("finish")

        self.assertEqual(result.code, 1, result)
        self.assertRegex(result.out, r"(?m)^FAILED cleanup-incomplete: 1 process still runs from "
                                     r"the invocation's workspace")
        self.assertIn("pid %d" % stray.pid, result.out)
        self.assertTrue(box.workspace().is_dir(), "nothing is removed from under a running process")
        self.assertEqual(box.run("status").code, 0, "the lock and the ledger stay open")

        stray.kill()
        stray.wait()
        again = box.run("finish")

        self.assertEqual(again.code, 0, again)
        self.assertRegex(again.out, r"(?m)^FINISH done ")

    def test_a_control_theme_the_store_kept_after_its_delete_keeps_the_invocation_open(self):
        box, themes, _ = started(self)
        box.edit_store(lambda s: s.update(deletes_ignored=[themes["control"]]))

        result = box.run("finish")

        self.assertEqual(result.code, 1, result)
        self.assertIn("FAILED cleanup-incomplete: the control theme %d is still in the theme "
                      "library" % themes["control"], result.out)
        self.assertEqual(box.run("status").code, 0, "the lock and the ledger stay open")

        box.edit_store(lambda s: s.update(deletes_ignored=[]))
        again = box.run("finish")

        self.assertEqual(again.code, 0, again)
        self.assertNotIn(themes["control"], box.theme_ids())


class FinishDeletesOnlyItsOwnThemes(unittest.TestCase):
    """The CLI's `theme delete --theme` deletes every theme whose id or name matches, so a
    delete passes the same guard a push does."""

    def test_a_theme_named_like_the_control_themes_id_stops_the_delete(self):
        box, themes, _ = started(self)
        named = str(themes["control"])
        box.edit_store(lambda s: next(t for t in s["themes"] if t["id"] == 101).update(name=named))

        result = box.run("finish")

        self.assertEqual(result.code, 1, result)
        self.assertEqual(result.lines("REFUSED"), [
            "REFUSED theme-name-clash: theme 101 is named %s, the id of the control theme, and "
            "the CLI matches names too" % named])
        self.assertTrue({101, themes["control"], themes["working"]} <= box.theme_ids())
        self.assertEqual(box.run("status").code, 0, "the lock and the ledger stay open")


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


class FinishDiscardsOnlyWhatNoRoundKept(unittest.TestCase):
    """`--discard` deletes the Working theme and the branch, so it waits for an open Round's
    verdict and refuses once any Round was kept: that work is the developer's to publish."""

    def assert_nothing_discarded(self, box, result, themes_before):
        self.assertEqual(result.code, 1, result)
        self.assertEqual(box.theme_ids(), themes_before, "a refused --discard deletes no theme")
        self.assertNotEqual(box.git(box.repo, "branch", "--list", "speed-tune/*"), "")
        self.assertEqual(box.run("status").code, 0, "the lock and the ledger stay open")

    def test_while_a_round_is_open_it_is_refused(self):
        box = pushed(self)
        themes_before = box.theme_ids()

        result = box.run("finish", "--discard")

        self.assertRegex(result.out, r"(?m)^REFUSED round-open: Round 1 is open")
        self.assert_nothing_discarded(box, result, themes_before)

    def test_once_a_round_was_kept_it_is_refused(self):
        box = ran(self, "reached")
        themes_before = box.theme_ids()

        result = box.run("finish", "--discard")

        self.assertEqual(result.lines("REFUSED"), [
            "REFUSED kept-rounds: Round 1 kept its change, so the Working theme %d and the branch "
            "hold work to publish" % WORKING])
        self.assertIn("NOTE Run `finish` without --discard: it keeps the Working theme and the "
                      "branch.", result.out)
        self.assert_nothing_discarded(box, result, themes_before)

    def test_after_rounds_that_were_all_removed_it_discards_both_themes_and_the_branch(self):
        box = pushed(self)
        self.assertEqual(box.run("verdict", "--remove").code, 0)
        themes = {WORKING, CONTROL}

        result = box.run("finish", "--discard")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(box.theme_ids() & themes, set())
        self.assertEqual(box.git(box.repo, "branch", "--list", "speed-tune/*"), "")


if __name__ == "__main__":
    unittest.main()
