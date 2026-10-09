"""scripts/test.sh: every test file in the repo's Python suites, each run as its own
unittest process, several at once.

Each test builds a throwaway folder of test files and runs the runner on it
through /bin/bash, which is bash 3.2 on a Mac and bash 5 in CI.
"""

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parent.parent / "test.sh"

PASSING = """
import unittest

class Passing(unittest.TestCase):
    def test_passes(self):
        pass
"""


FAILING = """
import unittest

class Failing(unittest.TestCase):
    def test_fails(self):
        self.fail("this file fails")
"""


class Tree:
    """A throwaway folder of test files for the runner to search."""

    def __init__(self, test):
        self.test = test
        self.root = Path(tempfile.mkdtemp(prefix="test-sh-"))
        test.addCleanup(shutil.rmtree, self.root, True)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(text))

    def run(self, jobs=None):
        env = dict(os.environ)
        env.pop("TEST_JOBS", None)
        if jobs is not None:
            env["TEST_JOBS"] = str(jobs)
        return subprocess.run(["/bin/bash", str(RUNNER), str(self.root)], env=env,
                              capture_output=True, text=True, timeout=120)

    def header(self, path):
        """The line the runner prints above a file's output."""
        return "== %s/%s" % (self.root, path)


def headers(done):
    return [line for line in done.stdout.splitlines() if line.startswith("== ")]


class APassingFile(unittest.TestCase):
    def test_runs_under_a_header_naming_it_and_the_runner_exits_0(self):
        tree = Tree(self)
        tree.write("skill/scripts/test_one.py", PASSING)

        done = tree.run()

        self.assertEqual(done.returncode, 0, done)
        self.assertEqual(headers(done), [tree.header("skill/scripts/test_one.py")])
        self.assertIn("Ran 1 test", done.stdout)


class AFailingFile(unittest.TestCase):
    def test_fails_the_run_and_every_file_after_it_still_runs(self):
        tree = Tree(self)
        tree.write("skill/scripts/test_a.py", FAILING + "# the bigger file, so it runs first\n" * 50)
        tree.write("skill/scripts/test_b.py", PASSING)

        done = tree.run(jobs=1)  # one at a time, biggest first: test_a.py fails first

        self.assertNotEqual(done.returncode, 0, done)
        self.assertEqual(headers(done), [tree.header("skill/scripts/test_a.py"),
                                         tree.header("skill/scripts/test_b.py")])
        self.assertIn("this file fails", done.stdout)
        self.assertEqual(done.stdout.count("Ran 1 test"), 2, done.stdout)


class TheFilesItFinds(unittest.TestCase):
    def test_are_the_test_star_py_files_outside_deprecated_and_the_hidden_folders(self):
        tree = Tree(self)
        tree.write("bucket/domain/skill/scripts/tests/test_kept.py", PASSING)
        tree.write("bucket/domain/skill/scripts/tests/support.py", FAILING)
        tree.write("deprecated/domain/skill/scripts/test_old.py", FAILING)
        tree.write(".claude/worktrees/copy/scripts/test_hidden.py", FAILING)

        done = tree.run()

        self.assertEqual(done.returncode, 0, done)
        self.assertEqual(headers(done), [tree.header("bucket/domain/skill/scripts/tests/test_kept.py")])

    def test_none_at_all_fails_the_run_so_a_broken_search_cannot_pass_as_green(self):
        tree = Tree(self)
        tree.write("bucket/domain/skill/scripts/convert.py", PASSING)

        done = tree.run()

        self.assertEqual(done.returncode, 1, done)
        self.assertEqual(headers(done), [])
        self.assertIn("no test*.py files under %s" % tree.root, done.stderr)


class EachFile(unittest.TestCase):
    def test_imports_the_helpers_beside_it_as_a_whole_folder_run_does(self):
        tree = Tree(self)
        tree.write("skill/scripts/tests/support.py", "ANSWER = 42\n")
        tree.write("skill/scripts/tests/test_uses_support.py", """
            import unittest
            from support import ANSWER

            class UsesSupport(unittest.TestCase):
                def test_reads_it(self):
                    self.assertEqual(ANSWER, 42)
            """)

        done = tree.run()

        self.assertEqual(done.returncode, 0, done)

    def test_runs_in_a_process_of_its_own(self):
        tree = Tree(self)
        for name in ("test_a", "test_b"):
            tree.write("skill/scripts/%s.py" % name, """
                import os
                import unittest

                class RecordsItsProcess(unittest.TestCase):
                    def test_records_it(self):
                        with open(__file__ + ".pid", "w") as f:
                            f.write(str(os.getpid()))
                """)

        done = tree.run()

        self.assertEqual(done.returncode, 0, done)
        pids = {(tree.root / "skill/scripts" / (name + ".py.pid")).read_text()
                for name in ("test_a", "test_b")}
        self.assertEqual(len(pids), 2, "both files ran in one process")


# Each file waits until the other has started: run one after the other, the first one
# waits in vain and fails.
WAITS_FOR_THE_OTHER = """
import os
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ME, OTHER = %r, %r

class WaitsForTheOther(unittest.TestCase):
    def test_sees_the_other_file_running(self):
        open(os.path.join(HERE, ME + ".started"), "w").close()
        deadline = time.monotonic() + 20
        while not os.path.exists(os.path.join(HERE, OTHER + ".started")):
            self.assertLess(time.monotonic(), deadline, "the other file never started")
            time.sleep(0.05)
"""


class Files(unittest.TestCase):
    def test_start_biggest_first_so_the_slowest_do_not_start_last(self):
        tree = Tree(self)
        tree.write("skill/scripts/test_a.py", PASSING)
        tree.write("skill/scripts/test_b.py", PASSING + "# more tests would go here\n" * 50)

        done = tree.run(jobs=1)

        self.assertEqual(done.returncode, 0, done)
        self.assertEqual(headers(done), [tree.header("skill/scripts/test_b.py"),
                                         tree.header("skill/scripts/test_a.py")])

    def test_run_at_the_same_time(self):
        tree = Tree(self)
        tree.write("skill/scripts/test_a.py", WAITS_FOR_THE_OTHER % ("a", "b"))
        tree.write("skill/scripts/test_b.py", WAITS_FOR_THE_OTHER % ("b", "a"))

        done = tree.run(jobs=2)

        self.assertEqual(done.returncode, 0, done)


if __name__ == "__main__":
    unittest.main()
