"""Samples: recorded from a Lighthouse report file, or taken by the pinned Lighthouse.

The fixtures are real Lighthouse 13.5.0 reports of a real store's published
pages, trimmed to the fields the program reads, with the store's identity
replaced by store.example. A broken Sample is derived from a real one by
editing the one field that breaks it.
"""

import json
import os
import shutil
import signal
import sys
import tempfile
import unittest
from pathlib import Path

import support
from support import Sandbox, read_report, report


def running(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def write_variant(box, name, change):
    """A copy of a real report with one field changed, as a file the program can read."""
    data = read_report(name)
    change(data)
    path = box.root / ("variant-%s.json" % name)
    path.write_text(json.dumps(data))
    return path


class RecordingASampleFromAReportFile(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox(self)
        self.box.start()

    def test_a_recorded_sample_carries_the_reports_metrics(self):
        result = self.box.run("sample", "--page", "home", "--device", "mobile",
                              "--report", report("home-mobile-1"))

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("SAMPLE"), [
            "SAMPLE s0001 baseline home mobile control | performance 36 | lcp 10157ms | "
            "tbt 1315ms | cls 0.000 | fcp 5208ms | si 5646ms | accessibility 94"])

    def test_a_report_with_a_runtime_error_is_rejected_and_not_recorded(self):
        broken = write_variant(self.box, "home-mobile-2", lambda r: r.update(
            runtimeError={"code": "NO_FCP", "message": "The page did not paint any content."}))

        result = self.box.run("sample", "--page", "home", "--device", "mobile", "--report", broken)

        self.assertEqual(result.code, 1, result)
        self.assertEqual(result.lines("SAMPLE"),
                         ["SAMPLE rejected home mobile control: runtime-error NO_FCP"])
        self.assertIn("MEASUREMENT baseline home mobile control incomplete 0/5",
                      self.box.run("status").out)

    def test_a_report_of_the_other_device_is_rejected(self):
        result = self.box.run("sample", "--page", "home", "--device", "desktop",
                              "--report", report("home-mobile-3"))

        self.assertEqual(result.lines("SAMPLE"),
                         ["SAMPLE rejected home desktop control: wrong-device mobile"])

    def test_a_redirected_page_is_rejected(self):
        moved = write_variant(self.box, "home-mobile-4", lambda r: r.update(
            mainDocumentUrl="https://store.example/password"))

        result = self.box.run("sample", "--page", "home", "--device", "mobile", "--report", moved)

        self.assertEqual(result.code, 1, result)
        self.assertEqual(result.lines("SAMPLE"), [
            "SAMPLE rejected home mobile control: redirected https://store.example/password"])

    def test_a_report_of_the_page_with_shopifys_preview_bar_is_rejected(self):
        with_bar = write_variant(self.box, "home-mobile-4", lambda r: r.update(
            requestedUrl="https://store.example/", mainDocumentUrl="https://store.example/"))

        result = self.box.run("sample", "--page", "home", "--device", "mobile", "--report", with_bar)

        self.assertEqual(result.code, 1, result)
        self.assertEqual(result.lines("SAMPLE"), [
            "SAMPLE rejected home mobile control: wrong-page https://store.example/"])

    def test_a_report_from_another_lighthouse_version_is_rejected(self):
        older = write_variant(self.box, "home-mobile-5",
                              lambda r: r.update(lighthouseVersion="12.8.2"))

        result = self.box.run("sample", "--page", "home", "--device", "mobile", "--report", older)

        self.assertEqual(result.lines("SAMPLE"),
                         ["SAMPLE rejected home mobile control: wrong-lighthouse 12.8.2"])

    def test_a_report_with_no_performance_score_is_rejected(self):
        unscored = write_variant(self.box, "home-mobile-1",
                                 lambda r: r["categories"]["performance"].update(score=None))

        result = self.box.run("sample", "--page", "home", "--device", "mobile", "--report", unscored)

        self.assertEqual(result.lines("SAMPLE"),
                         ["SAMPLE rejected home mobile control: no-score performance"])

    def test_the_preview_cookie_never_reaches_the_ledger_folder(self):
        secret = "_shopify_essential=do-not-store-this-value"
        with_cookie = write_variant(self.box, "home-mobile-1", lambda r: r["configSettings"].update(
            extraHeaders={"Cookie": secret}))

        self.box.run("sample", "--page", "home", "--device", "mobile", "--report", with_cookie)

        folder = self.box.repo / ".agent" / "shopify-speed-tune"
        stored = "".join(p.read_text() for p in folder.rglob("*") if p.is_file())
        self.assertIn("s0001", stored)
        self.assertNotIn("do-not-store-this-value", stored)


class TakingASample(unittest.TestCase):
    """The fake pnpm stands in for `pnpm dlx lighthouse@13.5.0` and holds the program
    to the real contract: an isolated pnpm store, the invocation's own Chrome already
    running at `--port` with the preview cookie in its jar and in no header, `?pb=0`
    on an unpublished theme's page, the URL first. It serves the theme the jar's
    cookie selects, and the preview query parameter redirects, as a real store does."""

    def setUp(self):
        self.box = Sandbox(self)
        self.box.start()

    def test_a_sample_runs_the_pinned_lighthouse_through_pnpm_on_the_invocations_chrome(self):
        result = self.box.run("sample", "--page", "home", "--device", "mobile", "--count", "1")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("SAMPLE"), [
            "SAMPLE s0001 baseline home mobile control | performance 36 | lcp 10157ms | "
            "tbt 1315ms | cls 0.000 | fcp 5208ms | si 5646ms | accessibility 94"])

    def test_a_desktop_sample_uses_lighthouses_desktop_preset(self):
        result = self.box.run("sample", "--page", "home", "--device", "desktop", "--count", "1")

        self.assertEqual(result.code, 0, result)
        self.assertRegex(result.out, r"(?m)^SAMPLE s0001 baseline home desktop control \| "
                                     r"performance 88 \| ")

    def test_a_control_theme_sample_carries_its_preview_cookie_in_the_browsers_jar(self):
        result = self.box.run("sample", "--page", "home", "--device", "mobile", "--count", "2")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(len(result.lines("SAMPLE")), 2)
        self.assertEqual(result.lines("FAILED"), [])

    def test_each_sample_gets_a_chrome_of_its_own_stopped_and_deleted_after_it(self):
        self.box.run("sample", "--page", "home", "--device", "mobile", "--count", "2")

        started = self.box.chromes_started()
        self.assertEqual(len(started), 2)
        for chrome in started:
            self.assertFalse(running(chrome["pid"]), "Chrome %d still runs" % chrome["pid"])
            self.assertFalse(os.path.exists(chrome["profile"]), "its profile is still there")

    def test_the_preview_cookie_reaches_no_report_ledger_or_output(self):
        result = self.box.run("sample", "--page", "home", "--device", "mobile", "--count", "1")

        self.assertEqual(result.code, 0, result)
        folder = self.box.repo / ".agent" / "shopify-speed-tune"
        kept = "".join(p.read_text() for p in folder.rglob("*") if p.is_file())
        for secret in self.box.secrets_seen():
            self.assertNotIn(secret, kept)
            self.assertNotIn(secret, result.out + result.err)

    def test_a_sample_that_lost_the_cookie_measured_the_published_theme_and_is_rejected(self):
        self.box.edit_store(lambda s: s["lighthouse"].update(drops_cookie=True))

        result = self.box.run("sample", "--page", "home", "--device", "mobile", "--count", "1")

        self.assertEqual(result.code, 1, result)
        self.assertIn("SAMPLE rejected home mobile control: wrong-theme no request under "
                      "/cdn/shop/t/23/", result.lines("SAMPLE"))
        self.assertIn("MEASUREMENT baseline home mobile control incomplete 0/5",
                      self.box.run("status").out)

    def test_without_a_count_it_fills_the_measurement(self):
        result = self.box.run("sample", "--page", "home", "--device", "mobile")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(len(result.lines("SAMPLE")), 5)
        self.assertRegex(result.out, r"(?m)^MEASUREMENT baseline home mobile control n=5 ")


def cutting_ps(test):
    """A folder holding a `ps` that cuts each line it prints at 80 columns unless asked for
    whole lines with -ww, as some Linux builds do when their output is piped."""
    folder = Path(tempfile.mkdtemp(prefix="speed-tune-ps-"))
    test.addCleanup(shutil.rmtree, folder, True)
    stand_in = folder / "ps"
    stand_in.write_text(
        "#!%s\n"
        "import subprocess, sys\n"
        "done = subprocess.run([%r] + sys.argv[1:], capture_output=True, text=True)\n"
        "out = done.stdout\n"
        "if '-ww' not in sys.argv[1:]:\n"
        "    out = '\\n'.join(line[:80] for line in out.split('\\n'))\n"
        "sys.stdout.write(out)\n"
        "sys.stderr.write(done.stderr)\n"
        "sys.exit(done.returncode)\n" % (sys.executable, shutil.which("ps")))
    stand_in.chmod(0o755)
    return str(folder)


class ASampleCutOffAtItsTimeLimit(unittest.TestCase):
    """When the invocation's Chrome is gone, Lighthouse's chrome-launcher starts a Chrome of
    its own, in a session of its own, so stopping Lighthouse leaves it running."""

    def test_stops_the_chrome_lighthouse_started_for_itself(self):
        box = Sandbox(self)
        box.start()
        box.edit_store(lambda s: s["lighthouse"].update(chrome_lost=True))
        self.addCleanup(self.clear_launcher_profiles, box)

        result = box.run("sample", "--page", "home", "--device", "mobile", "--count", "1",
                         env={"SPEED_TUNE_SAMPLE_SECONDS": "1",
                              "PATH": cutting_ps(self) + os.pathsep + box.env()["PATH"]})

        self.assertEqual(result.code, 1, result)
        self.assertIn("SAMPLE rejected home mobile control: timeout after 1 s", result.lines("SAMPLE"))
        launched = [c for c in box.chromes_started() if "lighthouse." in c["profile"]]
        self.assertEqual(len(launched), 3, "one Chrome of Lighthouse's own per attempt")
        for chrome in box.chromes_started():
            self.assertFalse(support.running(chrome["pid"]), "Chrome %d still runs" % chrome["pid"])

    @staticmethod
    def clear_launcher_profiles(box):
        """What a failing run of this test would leave: Lighthouse's own Chromes and profiles."""
        for chrome in box.chromes_started():
            if support.running(chrome["pid"]):
                os.kill(chrome["pid"], signal.SIGKILL)
        listed = box.root / "launcher-profiles"
        for profile in (listed.read_text().split() if listed.exists() else []):
            shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
