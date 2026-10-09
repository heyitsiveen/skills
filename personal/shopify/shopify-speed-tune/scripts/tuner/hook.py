"""The client repo's pre-commit hook, run the way git runs it before a commit.

Every kept Round is committed through the repo's own hooks, so a hook that
already fails on the unchanged repo would refuse every keep. `start` runs it
first, on the clean tree and before it creates anything: a failing hook
refuses the invocation, unless the developer approved committing this
invocation's kept Rounds with `--no-verify`.

The hook is the one git would run: under `core.hooksPath` when it is set (husky
v9 sets `.husky/_`), else `.git/hooks`, and only when it is executable. `git
hook run` runs it as `git commit` would; a git older than 2.36 has no such
command, and gets the hook file run from the repo root, as git itself does.

A failing hook is shown by how its output ends (`ending`): the lines that count
its problems, such as theme check's `733 total offenses` and `12 errors`, then
its last line, as a terminal would show them.

What the invocation keeps is the ledger's `hook` record, which the report
renders: {"status": "passed" | "absent" | "bypass-approved", "detail": text},
plus, for a bypassed hook, "output": the lines of its ending.
"""

import os
import re

from tuner import repo
from tuner.output import Refused
from tuner.proc import capture, child_env

PASSED, ABSENT, BYPASS = "passed", "absent", "bypass-approved"
FLAG = "--no-verify-approved"
HOOK_RUN = (2, 36)  # the first git with `git hook run`
SECONDS = 300
ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-Z\\-_])")
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
# Box drawing a CLI frames its messages with: a line from a left corner to a right one is a
# box's top or bottom edge, and the sides come off each line's ends.
LEFT_CORNERS, RIGHT_CORNERS = "╭╰┌└╔╚", "╮╯┐┘╗╝"
SIDES = "│┃║╭╮╯╰─━═┌┐└┘├┤┬┴┼╔╗╚╝ "
WIDTH = 160  # characters a line keeps; a longer one is cut, ending in "..."
# A line that counts problems: `733 total offenses`, `12 errors.`, `21 info issues.`,
# `5 problems (5 errors, 0 warnings)`.
SUMMARY = re.compile(r"\b\d[\d,]*\s+(?:[a-z]+\s+)?(?:problems?|offen[cs]es?|errors?|warnings?|"
                     r"issues?)\b", re.I)
ENDING_LINES = 5


class Hook:
    """The repo's pre-commit hook as `start` found it."""

    def __init__(self, status, path=None, code=None, output=""):
        self.status = status
        self.path = path        # as shown: relative to the repo root when inside it
        self.code = code        # its exit code, or None when it did not finish
        self.output = output

    def record(self):
        """The ledger's `hook` record."""
        if self.status == ABSENT:
            return {"status": ABSENT,
                    "detail": "No pre-commit hook is active, so keep commits run none."}
        if self.status == PASSED:
            return {"status": PASSED,
                    "detail": "The pre-commit hook %s passes on the unchanged repo, so every "
                              "keep commit runs it." % self.path}
        said = ending(self.output)
        return {"status": BYPASS, "output": said,
                "detail": "The pre-commit hook %s %s on the unchanged repo (%s). The developer "
                          "approved committing this invocation's kept Rounds with --no-verify."
                          % (self.path, self.outcome(), " | ".join(said) or "no output")}

    def outcome(self):
        if self.code is None:
            return "did not finish within %d s" % seconds()
        return "exits %d" % self.code

    def line(self):
        """The START line: the status, where the hook is, and how a bypassed one ended."""
        parts = ["hook=%s" % self.status]
        if self.path:
            parts.append("path=%s" % self.path)
        if self.status == BYPASS:
            parts.append("exit=%s" % ("timeout" if self.code is None else self.code))
        return " ".join(parts)

    def notes(self, approved):
        """What the developer's approval does here: bypass the hook, or nothing."""
        if self.status == BYPASS:
            return ["kept Rounds are committed with --no-verify, as the developer approved for "
                    "this invocation"]
        if not approved:
            return []
        if self.status == PASSED:
            return ["the pre-commit hook passes, so kept Rounds are committed through it and "
                    "%s goes unused" % FLAG]
        return ["no pre-commit hook is active, so %s goes unused" % FLAG]


def seconds():
    return int(os.environ.get("SPEED_TUNE_HOOK_SECONDS", SECONDS))


def active(root):
    """The pre-commit hook git would run in `root`, as an absolute path, or None."""
    found = repo.git(root, "rev-parse", "--git-path", "hooks/pre-commit").stdout.strip()
    path = os.path.realpath(os.path.join(root, found))
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path
    return None


def run(root, path):
    """(exit code, or None when it was stopped at the time limit; its output, both streams)."""
    argv = ["git", "hook", "run", "pre-commit"] if repo.git_version(root) >= HOOK_RUN else [path]
    return capture(argv, cwd=root, env=child_env(), timeout=seconds())


def readable(output):
    """The output's lines as a terminal shows them: colour codes, control characters and
    box drawing gone, a line rewritten in place by a carriage return read as it was left,
    blank lines dropped, and each line cut to WIDTH characters."""
    lines = []
    for raw in ANSI.sub("", output or "").split("\n"):
        line = CONTROL.sub("", raw.rstrip("\r").rsplit("\r", 1)[-1]).strip()
        if not line or (line[0] in LEFT_CORNERS and line[-1] in RIGHT_CORNERS):
            continue
        line = " ".join(line.strip(SIDES).split())
        if line:
            lines.append(line if len(line) <= WIDTH else line[:WIDTH - 3].rstrip() + "...")
    return lines


def ending(output):
    """How a hook's output ends, in at most ENDING_LINES readable lines: its summary, the
    last run of lines that count problems, then its last line; or, when no line counts
    problems, its last three lines."""
    lines = readable(output)
    counted = [n for n, line in enumerate(lines) if SUMMARY.search(line)]
    if not counted:
        return lines[-3:]
    first = last = counted[-1]
    while first - 1 in counted:
        first -= 1
    said = lines[first:last + 1][:ENDING_LINES - 1]
    return said + lines[-1:] if last < len(lines) - 1 else said


def check(root, approved):
    """The repo's pre-commit hook, run on the unchanged repo; a refusal when it fails and
    the developer has not approved committing without it."""
    path = active(root)
    if path is None:
        return Hook(ABSENT)
    shown = os.path.relpath(path, root) if path.startswith(root + os.sep) else path
    code, output = run(root, path)
    if code == 0:
        return Hook(PASSED, shown, code, output)
    found = Hook(BYPASS, shown, code, output)
    if approved:
        return found
    said = " | ".join(ending(output))
    raise Refused("pre-commit-fails", "the pre-commit hook %s %s on the unchanged repo%s"
                  % (shown, found.outcome(), ": " + said if said else ", with no output"),
                  "Every kept Round is committed through this hook, so it would refuse every "
                  "keep. Fix what it reports and commit the fix, then run `start` again.",
                  "Only when the developer approves it for this invocation, run `start` again "
                  "with %s: kept Rounds are then committed with --no-verify." % FLAG)


def verifies(data):
    """Whether keep commits run the repo's hooks: always, unless the developer approved
    bypassing a hook that already failed at start."""
    return (data.get("hook") or {}).get("status") != BYPASS
