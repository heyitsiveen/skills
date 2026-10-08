"""A Round's change: the theme files the working tree changes against the Round's base commit.

A Round opens on a clean tree and records its base commit and the untracked
files already there, so its change is exactly what was edited since: tracked
files that differ from the base, plus untracked files that are new. Each entry
is (status, path) with status M (modified), A (added) or D (deleted).

The guards a change must pass before it may reach a theme live here too, and so
does putting the tree back to the base commit for those paths.
"""

import hashlib
import os
import re

from tuner import repo
from tuner.output import Failed, Refused
from tuner.proc import run

SETTINGS = "config/settings_data.json"
THEME_FOLDERS = ("assets", "blocks", "config", "layout", "locales", "sections", "snippets",
                 "templates")
# Template JSON and section groups: page content the merchant edits in the theme editor.
TEMPLATE_JSON = re.compile(r"templates/.+\.json|sections/[^/]+\.json")
# How far git looks for a NUL byte before it calls a file binary.
BINARY_PROBE = 8000

# Ways a page can tell Lighthouse, its emulated phone or its platform from a
# visitor, after Shopify's guide to fake performance apps. Liquid cannot see the
# user agent, so detection always arrives as text in a file; any added line that
# carries one of these is refused, comments included, since a text rule cannot
# tell a comment from code and an honest change never needs these words.
DETECTION = (
    re.compile(r"navigator\s*(?:\.\s*|\[\s*['\"])(?:userAgent(?:Data)?|platform|webdriver|plugins)\b",
               re.I),
    re.compile(r"\buserAgent(?:Data)?\b", re.I),
    re.compile(r"\}\s*=\s*(?:window\s*\.\s*)?navigator\b", re.I),
    re.compile(r"lighthouse|pagespeed|speed\s*insights|gtmetrix|headless\s*chrome", re.I),
    re.compile(r"\bmoto\s*g|linux\s*x86[_-]64|\\x4c\\x69\\x6e\\x75\\x78", re.I),
    re.compile(r"__native(?:Promise|Performance)|isAuditBot", re.I),
)


def untracked(root):
    proc = repo.git(root, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted(p for p in proc.stdout.split("\0") if p)


def compute(root, base, snapshot):
    """[(status, path)] of the working tree against `base`, sorted by path."""
    proc = repo.git(root, "diff", "--name-status", "--no-renames", "--no-ext-diff", "-z",
                    base, "--")
    parts = proc.stdout.split("\0")
    entries = {}
    for status, path in zip(parts[0::2], parts[1::2]):
        if status and path:
            entries[path] = "M" if status[0] == "T" else status[0]
    for path in untracked(root):
        if path not in snapshot:
            entries[path] = "A"
    return sorted(((status, path) for path, status in entries.items()), key=lambda e: e[1])


def is_template_json(path):
    return bool(TEMPLATE_JSON.fullmatch(path))


def added_lines(root, base, status, path):
    """[(line number, text)] the change adds to `path`: every line of a new file.

    A file is binary, as git decides, when a NUL byte comes in its first 8000:
    an image or a font has no line to read. Any other file is text, whatever its
    encoding: bytes that are not UTF-8, as in a Latin-1 library, read as U+FFFD,
    so every ASCII word the detection looks for still reads.
    """
    full = os.path.join(root, path)
    if status == "D" or not os.path.isfile(full):
        return []
    tracked = repo.git(root, "cat-file", "-e", "%s:%s" % (base, path)).returncode == 0
    if not tracked:
        with open(full, "rb") as f:
            data = f.read()
        if b"\0" in data[:BINARY_PROBE]:
            return []
        return list(enumerate(data.decode("utf-8", "replace").splitlines(), 1))
    diff = repo.git(root, "diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv",
                    base, "--", path, errors="replace").stdout
    out, number = [], 0
    for line in diff.splitlines():
        hunk = re.match(r"@@ -\S+ \+(\d+)", line)
        if hunk:
            number = int(hunk.group(1))
        elif line.startswith("+") and not line.startswith("+++ "):
            out.append((number, line[1:]))
            number += 1
    return out


def check(root, base, entries):
    """Refuse a change that is not theme code, touches the merchant's settings file,
    names a path the CLI would read as a pattern, or adds a way to detect the test."""
    for _, path in entries:
        if path.split("/", 1)[0] not in THEME_FOLDERS or "/" not in path:
            raise Refused("outside-theme", "the change touches %s, which is not theme code" % path,
                          "A Round changes theme files only; undo that part and push again.")
    for _, path in entries:
        if path == SETTINGS:
            raise Refused("settings-file", "the change touches %s, the merchant's theme settings "
                          "file" % SETTINGS,
                          "Going live would overwrite the merchant's own edits. Restore it with "
                          "`git checkout HEAD -- %s` and push again; when the item needs a "
                          "setting, it is the merchant's to change." % SETTINGS)
    for status, path in entries:
        for number, text in added_lines(root, base, status, path):
            for pattern in DETECTION:
                found = pattern.search(text)
                if found:
                    raise Refused("detection", "%s line %d adds %s" % (path, number, found.group(0)),
                                  "Telling Lighthouse, its test phone or the platform from a "
                                  "visitor fakes the score, so no Round may add it, not even in "
                                  "a comment. Remove that line and push again.")


def hashes(root, paths):
    """{path: sha256 of its content now, or None when it does not exist}."""
    out = {}
    for path in paths:
        full = os.path.join(root, path)
        if os.path.isfile(full):
            with open(full, "rb") as f:
                out[path] = hashlib.sha256(f.read()).hexdigest()
        else:
            out[path] = None
    return out


def fingerprint(root, entries):
    """One hash of the change: every path, its status and its content now."""
    digest = hashlib.sha256()
    now = hashes(root, [p for _, p in entries])
    for status, path in entries:
        digest.update(("%s %s %s\0" % (status, path, now[path])).encode("utf-8"))
    return digest.hexdigest()


def restore(root, base, paths):
    """Put `paths` back as the base commit has them, in the index and the working tree."""
    listed = repo.git(root, "ls-tree", "-r", "--name-only", "-z", base, "--", *paths).stdout
    known = {p for p in listed.split("\0") if p}
    if known:
        proc = repo.git(root, "checkout", base, "--", *sorted(known))
        if proc.returncode != 0:
            raise Failed("restore-failed", "git could not restore %s: %s"
                         % (", ".join(sorted(known)), proc.stderr.strip()[-300:]))
    added = [p for p in paths if p not in known]
    if added:
        repo.git(root, "rm", "-q", "--cached", "--ignore-unmatch", "--", *added)
        for path in added:
            full = os.path.join(root, path)
            if os.path.isfile(full):
                os.remove(full)


class Committed:
    def __init__(self, sha=None, output=None):
        self.sha = sha
        self.output = output


def commit(root, base, paths, subject, body, verify=True):
    """Commit exactly `paths` as one commit on `base`, running the repo's own hooks
    unless `verify` is False (the developer approved --no-verify at start).

    Returns Committed(sha) or, when git or a hook refuses, Committed(output=its
    last lines) with nothing committed and the paths unstaged.
    """
    repo.git(root, "add", "-A", "--", *paths)
    staged = {p for p in repo.git(root, "diff", "--cached", "--name-only", "-z").stdout.split("\0") if p}
    if staged - set(paths):
        raise Failed("commit-unexpected", "the index also holds %s, which is not the Round's "
                     "change" % ", ".join(sorted(staged - set(paths))),
                     "Unstage it with `git restore --staged <path>` and run `verdict` again.")
    proc = run(["git", "commit", "-q", *([] if verify else ["--no-verify"]), "-m", subject,
                "-m", body], cwd=root, timeout=900)
    if proc.returncode != 0:
        repo.git(root, "reset", "-q", "--", *paths)
        lines = [l for l in (proc.stderr + "\n" + proc.stdout).splitlines() if l.strip()]
        return Committed(output=lines[-5:] or ["git commit exited %d" % proc.returncode])
    sha = repo.head(root)
    parent = repo.git(root, "rev-parse", sha + "^").stdout.strip()
    touched = {p for p in repo.git(root, "diff", "--name-only", "-z", base, sha).stdout.split("\0")
               if p}
    if parent != base or touched - set(paths):
        raise Failed("commit-unexpected", "commit %s is not one commit of the Round's change on %s"
                     % (sha[:12], base[:12]),
                     "Stop the Rounds and show the developer: a hook may have committed more.")
    if repo.git(root, "status", "--porcelain", "--", *paths).stdout.strip():
        raise Failed("commit-unexpected", "a commit hook left changes to the Round's files "
                     "uncommitted", "Stop the Rounds and show the developer.")
    return Committed(sha=sha)
