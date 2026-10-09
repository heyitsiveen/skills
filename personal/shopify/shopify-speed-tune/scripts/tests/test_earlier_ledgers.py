"""A ledger an earlier release wrote, read and finished by this one.

An invocation runs for hours and can outlive the release that started it: the
first real invocation paused at its plan stop under one release and carries on
under the next. The fixture is that invocation's ledger, key for key as the
earlier release wrote it, with the store's identity replaced (store.example,
live theme 100, Working 200, Control 201) and its repo, workspace and start
commit left as placeholders the sandbox fills in. That release saved Chrome for
Testing's preferences with no digest of them, so `finish` has nothing recorded
to read them back against but the copy `start` exported.
"""

import json
import plistlib
import subprocess
import unittest

from support import FAKES, HERE, Sandbox

LEDGER = HERE / "fixtures" / "ledgers" / "paused-at-the-plan-stop.json"
INVOCATION = "20261008-213521"
CFT_DOMAIN = "com.google.chrome.for.testing"
# What Chrome for Testing's preferences held before the invocation, as `start` exported them.
BEFORE = {"LastRunAppBundlePath": "/Users/dev/old-checker/Google Chrome for Testing.app"}


def paused(test):
    """A sandbox in which the paused invocation is the open one: its ledger in the repo, its
    branch checked out, its two themes in the store's theme library, its workspace holding the
    preferences `start` exported, the caffeinate it holds, and the machine lock. Chrome for
    Testing has since recorded itself in its preferences, as it does on every launch."""
    box = Sandbox(test)
    box.git(box.repo, "switch", "-q", "-c", "speed-tune/" + INVOCATION)
    workspace = box.tmp / ("shopify-speed-tune-%s-paused" % INVOCATION)
    workspace.mkdir()
    (workspace / "cft-preferences.plist").write_bytes(plistlib.dumps(BEFORE))
    domain = box.root / "defaults" / (CFT_DOMAIN + ".plist")
    domain.parent.mkdir()
    domain.write_bytes(plistlib.dumps({"LastRunAppBundlePath": str(
        workspace / "chrome" / "Google Chrome for Testing.app")}))

    awake = subprocess.Popen([str(FAKES / "caffeinate")], env=box.env(),
                             stdin=subprocess.DEVNULL)
    test.addCleanup(awake.wait)
    test.addCleanup(awake.kill)
    started = subprocess.run(["ps", "-ww", "-o", "lstart=", "-p", str(awake.pid)],
                             capture_output=True, text=True).stdout.strip()

    text = LEDGER.read_text(encoding="utf-8")
    for placeholder, value in (("<repo>", box.repo), ("<workspace>", workspace),
                               ("<start-commit>", box.git(box.repo, "rev-parse", "HEAD"))):
        text = text.replace(placeholder, str(value))
    data = json.loads(text)
    data["awake"] = {"pid": awake.pid, "started": started}
    ledger = box.repo / ".agent" / "shopify-speed-tune" / INVOCATION / "ledger.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps(data, indent=2))

    box.edit_store(lambda s: s["themes"].extend(
        {"id": theme["id"], "name": theme["name"], "role": "unpublished", "processing": False}
        for theme in data["themes"].values()))
    box.lock.parent.mkdir(parents=True)
    box.lock.write_text(json.dumps({
        "invocation": INVOCATION, "store": data["store"]["url"], "repo": str(box.repo),
        "ledger": str(ledger), "workspace": str(workspace), "started_at": data["created_at"],
        "last_op": "plan", "last_op_at": data["plan"]["recorded_at"], "awake": data["awake"]}))
    return box, workspace, domain


class TheInvocationPausedAtThePlanStop(unittest.TestCase):
    def setUp(self):
        self.box, self.workspace, self.domain = paused(self)

    def test_status_reads_it_and_judges_its_smoke_check_by_the_rule_in_force(self):
        result = self.box.run("status", "--invocation", INVOCATION)

        self.assertEqual(result.code, 0, result)
        self.assertEqual(result.lines("INVOCATION"), [
            "INVOCATION 20261008-213521 state=open store=https://store.example/ "
            "requested_score=80 hook=bypass-approved"])
        measured = result.lines("MEASUREMENT")
        self.assertEqual(len(measured), 9, result)
        self.assertEqual(measured[0], (
            "MEASUREMENT baseline home mobile control n=5 | performance 54 [47-59] | lcp 8634ms "
            "[8339-15891ms] | tbt 501ms [361-581ms] | cls 0.000 [0.000-0.000] | fcp 3592ms "
            "[3576-3753ms] | si 3753ms [3576-6715ms] | accessibility 94 [94-94]"))
        self.assertEqual(result.lines("CEILING"), [
            "CEILING home ceiling=60 requested=80 target=60",
            "CEILING collection ceiling=77 requested=80 target=77",
            "CEILING product ceiling=62 requested=80 target=62"])
        self.assertEqual(result.lines("PLAN"), ["PLAN draft items=5 used=0"])
        # Recorded as `fail: 2 missing app blocks` when each theme's token was held against it.
        self.assertEqual(result.lines("SMOKE"), ["SMOKE baseline result pass"])

    def test_finish_puts_chrome_for_testings_preferences_back_and_reads_them_back(self):
        result = self.box.run("finish")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(plistlib.loads(self.domain.read_bytes()), BEFORE)
        self.assertEqual(result.lines("FINISH")[-5:], [
            "FINISH verified themes control=gone working=unpublished",
            "FINISH verified branch=speed-tune/%s repo-on=main" % INVOCATION,
            "FINISH verified chrome=none workspace=gone awake=stopped preferences=as-before",
            "FINISH lock released",
            "FINISH done invocation=%s" % INVOCATION])

    def test_finish_says_so_when_the_copy_start_saved_is_gone_and_still_finishes(self):
        (self.workspace / "cft-preferences.plist").unlink()
        chrome_left = self.domain.read_bytes()

        result = self.box.run("finish")

        self.assertEqual(result.code, 0, result)
        self.assertEqual(self.domain.read_bytes(), chrome_left, "nothing to put back")
        self.assertRegex(result.out, r"(?m)^NOTE Chrome for Testing's preferences were not put "
                                     r"back or checked: the copy `start` saved, \S+, is gone")
        self.assertIn("FINISH verified chrome=none workspace=gone awake=stopped "
                      "preferences=unchecked", result.lines("FINISH"))
        self.assertRegex(result.out, r"(?m)^FINISH done ")


if __name__ == "__main__":
    unittest.main()
