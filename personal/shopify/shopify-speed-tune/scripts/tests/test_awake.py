"""Keeping the Mac awake for the invocation.

On battery a Mac sleeps when idle, even in the middle of a Measurement. `start`
holds one `caffeinate -i` for the whole invocation, and `finish` or `unlock`
stops it by the pid it recorded: never by name, and leaving no process behind.
Where there is no `caffeinate`, the invocation runs without one, quietly.
"""

import os
import re
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

from support import FAKES, STORE_URL, Sandbox, running


def gone(pid, wait=5.0):
    deadline = time.monotonic() + wait
    while running(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    return not running(pid)


class StartHoldsTheMacAwake(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox(self)
        _, self.started = self.box.start()
        held = self.box.awake_started(expected=1)
        self.assertEqual(len(held), 1, "start holds exactly one caffeinate")
        self.held = held[0]

    def test_with_one_idle_sleep_assertion_for_the_whole_invocation(self):
        self.assertEqual(self.held["args"], ["-i"])
        self.assertTrue(running(self.held["pid"]))
        self.assertIn("START awake pid=%d" % self.held["pid"], self.started.lines("START"))

    def test_finish_stops_it(self):
        result = self.box.run("finish")

        self.assertEqual(result.code, 0, result)
        self.assertIn("FINISH awake released", result.lines("FINISH"))
        self.assertTrue(gone(self.held["pid"]), "caffeinate still runs after finish")

    def test_unlock_stops_it(self):
        invocation = re.search(r"^START invocation=(\S+)", self.started.out, re.M).group(1)

        result = self.box.run("unlock", "--invocation", invocation)

        self.assertEqual(result.code, 0, result)
        self.assertIn("UNLOCK awake released", result.lines("UNLOCK"))
        self.assertTrue(gone(self.held["pid"]), "caffeinate still runs after unlock")

    def test_a_process_that_already_ended_is_not_signalled_again(self):
        os.kill(self.held["pid"], 15)
        self.assertTrue(gone(self.held["pid"]))

        result = self.box.run("finish")

        self.assertEqual(result.code, 0, result)
        self.assertNotIn("FINISH awake released", result.lines("FINISH"))
        self.assertRegex(result.out, r"(?m)^FINISH done ")


class AStartThatFailsPartWay(unittest.TestCase):
    def test_finish_discard_stops_it_too(self):
        box = Sandbox(self)
        box.edit_store(lambda s: s.update(duplicate_errors_after=1))
        box.publish_repo()
        started = box.run("start", "--store", STORE_URL)
        self.assertEqual(started.code, 1, started)
        held = box.awake_started(expected=1)

        box.run("finish", "--discard")

        self.assertEqual(len(held), 1)
        self.assertTrue(gone(held[0]["pid"]))


class WithoutCaffeinate(unittest.TestCase):
    """A PATH holding every stand-in but caffeinate, plus git and python3, as on a
    machine that is not a Mac."""

    def path_without_caffeinate(self):
        folder = Path(tempfile.mkdtemp(prefix="speed-tune-bin-"))
        self.addCleanup(shutil.rmtree, folder, True)
        for fake in FAKES.iterdir():
            if fake.name != "caffeinate":
                (folder / fake.name).symlink_to(fake)
        (folder / "git").symlink_to(shutil.which("git"))
        (folder / "python3").symlink_to(sys.executable)
        return str(folder)

    def test_the_invocation_runs_without_holding_anything(self):
        box = Sandbox(self)
        path = {"PATH": self.path_without_caffeinate()}
        box.publish_repo()

        started = box.run("start", "--store", STORE_URL, env=path)
        finished = box.run("finish", env=path)

        self.assertEqual(started.code, 0, started)
        self.assertEqual([l for l in started.lines("START") if "awake" in l], [])
        self.assertEqual(finished.code, 0, finished)
        self.assertEqual(box.awake_started(), [])


if __name__ == "__main__":
    unittest.main()
