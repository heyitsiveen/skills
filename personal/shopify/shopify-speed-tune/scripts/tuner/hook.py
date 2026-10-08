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

What the invocation keeps is the ledger's `hook` record, which the report
renders: {"status": "passed" | "absent" | "bypass-approved", "detail": text}.
"""

import os
import re
import signal
import subprocess

from tuner import repo
from tuner.output import Refused
from tuner.proc import child_env, require

PASSED, ABSENT, BYPASS = "passed", "absent", "bypass-approved"
FLAG = "--no-verify-approved"
HOOK_RUN = (2, 36)  # the first git with `git hook run`
SECONDS = 300
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
BOX = "│┃║╭╮╯╰─━═┌┐└┘├┤┬┴┼ "


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
            detail = "No pre-commit hook is active, so keep commits run none."
        elif self.status == PASSED:
            detail = ("The pre-commit hook %s passes on the unchanged repo, so every keep commit "
                      "runs it." % self.path)
        else:
            detail = ("The pre-commit hook %s %s on the unchanged repo (%s). The developer approved "
                      "committing this invocation's kept Rounds with --no-verify."
                      % (self.path, self.outcome(), tail(self.output) or "no output"))
        return {"status": self.status, "detail": detail}

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
    require(argv[0])
    proc = subprocess.Popen(argv, cwd=root, env=child_env(), stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            errors="replace", start_new_session=True)
    try:
        output, _ = proc.communicate(timeout=seconds())
        return proc.returncode, output
    except subprocess.TimeoutExpired:
        pass
    # The hook's own children (node, theme check) share the process group it leads.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        output, _ = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:  # a child that left the group still holds the output
        output = ""
    return None, output


def tail(output, lines=3, width=240):
    """The last few lines of a hook's output on one line, without colour or box drawing."""
    kept = []
    for line in ANSI.sub("", output or "").splitlines():
        line = " ".join(line.strip(BOX).split())
        if line:
            kept.append(line)
    text = " | ".join(kept[-lines:])
    return text if len(text) <= width else "..." + text[-(width - 3):]


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
    ending = tail(output)
    raise Refused("pre-commit-fails", "the pre-commit hook %s %s on the unchanged repo%s"
                  % (shown, found.outcome(), ": " + ending if ending else ", with no output"),
                  "Every kept Round is committed through this hook, so it would refuse every "
                  "keep. Fix what it reports and commit the fix, then run `start` again.",
                  "Only when the developer approves it for this invocation, run `start` again "
                  "with %s: kept Rounds are then committed with --no-verify." % FLAG)


def verifies(data):
    """Whether keep commits run the repo's hooks: always, unless the developer approved
    bypassing a hook that already failed at start."""
    return (data.get("hook") or {}).get("status") != BYPASS
