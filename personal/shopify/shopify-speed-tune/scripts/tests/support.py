"""Scaffolding for the decision program's tests.

Each test gets a Sandbox: a throwaway client theme repo, a fake store behind
fake `shopify`, `curl`, `pnpm` and `node` executables placed first on the path
(pnpm installs a stand-in Chrome for Testing), and its own machine lock and
temp dir. The program is driven only through its command
line, the way the skill drives it.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROGRAM = HERE.parent / "speed_tune.py"
FAKES = HERE / "fakes"
REPORTS = HERE / "fixtures" / "lighthouse"
SMOKE_RESULTS = HERE / "fixtures" / "smoke" / "results.json"

STORE_URL = "https://store.example/"
MYSHOPIFY = "example-store.myshopify.com"
LIVE_THEME = 100
THEME_FOLDERS = ("assets", "blocks", "config", "layout", "locales", "sections", "snippets",
                 "templates")
# The asset folder the fixtures' theme requests come from: /cdn/shop/t/23/.
CONTROL_ASSET_NUMBER = 23


def report(name):
    """Path of a real Lighthouse report fixture, by its file stem."""
    return REPORTS / (name + ".json")


def read_report(name):
    with open(report(name), encoding="utf-8") as f:
        return json.load(f)


# What a Golden repo's pre-commit hook does on its unchanged tree: lint-staged finds
# nothing staged, then a whole-theme `shopify theme check --fail-level=info` fails.
FAILING_HOOK = ("echo 'No staged files found.'\n"
                "echo 'snippets/image.liquid:3 MissingAsset' >&2\n"
                "echo '733 problems found in 412 files' >&2\n"
                "exit 1\n")


def hook(repo, script, path=".git/hooks/pre-commit"):
    """Install `script` as an executable shell hook at `path` in the client repo."""
    target = Path(repo) / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/bin/sh\n" + script)
    target.chmod(0o755)
    return target


def running(pid):
    """True while `pid` is a live process; a zombie waiting for its reaper is not."""
    state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True,
                           text=True).stdout.strip()
    return bool(state) and not state.startswith("Z")


class Result:
    def __init__(self, completed):
        self.code = completed.returncode
        self.out = completed.stdout
        self.err = completed.stderr

    def lines(self, tag):
        """Every stdout line that starts with the fixed tag, e.g. "REFUSED"."""
        return [l for l in self.out.splitlines() if l.startswith(tag + " ") or l == tag]

    def __repr__(self):
        return "exit %d\n--- stdout\n%s--- stderr\n%s" % (self.code, self.out, self.err)


class Sandbox:
    def __init__(self, test, root=None):
        self.test = test
        self.root = root or Path(tempfile.mkdtemp(prefix="speed-tune-test-"))
        test.addCleanup(shutil.rmtree, self.root, True)
        self.repo = self.root / "repo"
        self.tmp = self.root / "tmp"
        self.lock = self.root / "machine" / "speed-tune.lock"
        self.store_file = self.root / "store.json"
        if root is None:
            self.tmp.mkdir()
            self.write_store(self.default_store())
            self.make_repo(self.repo)

    @classmethod
    def restored(cls, test, root, frozen):
        """A sandbox put back at `root` from the copy `frozen` taken of it.

        Every path the ledger, the lock and the fake store hold lies under
        `root`, so a copy restored at the same path is the same invocation.
        """
        shutil.rmtree(root, ignore_errors=True)
        shutil.copytree(frozen, root, symlinks=True)
        return cls(test, root)

    # -- the fake store ---------------------------------------------------

    @staticmethod
    def default_store():
        return {
            "shop": {"name": "Example store", "domain": "store.example",
                     "url": "https://store.example", "myshopify_domain": MYSHOPIFY},
            "themes": [
                {"id": LIVE_THEME, "name": "example/main", "role": "live", "processing": False},
                {"id": 101, "name": "Old draft", "role": "unpublished", "processing": False},
                {"id": 102, "name": "Development (abc)", "role": "development", "processing": False},
            ],
            "next_theme_id": 200,
            # Each theme serves its files from its own /cdn/shop/t/<n>/ folder. The
            # fixtures' requests use 23, so the Control theme (the second copy) gets it.
            "asset_numbers": {str(LIVE_THEME): 7},
            "next_asset_number": CONTROL_ASSET_NUMBER - 1,
            "lighthouse": {
                "mobile": [str(report("home-mobile-%d" % i)) for i in range(1, 6)],
                "desktop": [str(report("home-desktop-1"))],
            },
            # What the smoke checker reports, each run rendered by the theme its cookie selects.
            "smoke_results": str(SMOKE_RESULTS),
        }

    def store(self):
        with open(self.store_file, encoding="utf-8") as f:
            return json.load(f)

    def write_store(self, state):
        with open(self.store_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def edit_store(self, change):
        state = self.store()
        change(state)
        self.write_store(state)

    def theme_ids(self):
        return {t["id"] for t in self.store()["themes"]}

    # -- the invocation's workspace and its browsers ----------------------

    def workspace(self):
        found = [p for p in self.tmp.iterdir() if p.name.startswith("shopify-speed-tune-")]
        self.test.assertEqual(len(found), 1, "one invocation workspace expected")
        return found[0]

    def chromes_started(self):
        """Every stand-in Chrome the program started: its pid and profile."""
        registry = self.root / "chromes"
        if not registry.is_dir():
            return []
        return [json.loads(p.read_text()) for p in sorted(registry.iterdir()) if p.name.isdigit()]

    def awake_started(self, expected=0, wait=5.0):
        """Every stand-in `caffeinate` the program started: its pid and arguments.

        A stand-in registers itself a moment after it starts, so this waits up to
        `wait` seconds for `expected` of them.
        """
        registry = self.root / "awake"
        deadline = time.monotonic() + wait
        while True:
            found = [json.loads(p.read_text()) for p in sorted(registry.iterdir())
                     if p.name.isdigit()] if registry.is_dir() else []
            if len(found) >= expected or time.monotonic() > deadline:
                return found
            time.sleep(0.05)

    def secrets_seen(self):
        """Every preview cookie value the fake store handed out, as it would appear anywhere."""
        return ["fake-%d-cookie" % t["id"] for t in self.store()["themes"]]

    # -- client theme repos -----------------------------------------------

    def make_repo(self, path, store=MYSHOPIFY, toml=None):
        """A client theme repo as the client-theme skills keep one: `shopify.theme.toml` at
        its root and `.agent/` beside it, both kept out of git through .git/info/exclude."""
        (path / "layout").mkdir(parents=True)
        (path / "config").mkdir()
        (path / "layout" / "theme.liquid").write_text("<html>{{ content_for_header }}</html>\n")
        (path / "config" / "settings_schema.json").write_text("[]\n")
        if toml is None:
            toml = '[environments.default]\nstore = "%s"\n' % store
        (path / "shopify.theme.toml").write_text(toml)
        self.git(path, "init", "-q", "-b", "main")
        with open(path / ".git" / "info" / "exclude", "a", encoding="utf-8") as f:
            f.write(".agent/\nshopify.theme.toml\n")
        self.git(path, "add", "-A")
        self.git(path, "commit", "-q", "-m", "init")
        return path

    def git(self, path, *args):
        return subprocess.run(["git", *args], cwd=path, env=self.env(), check=True,
                              capture_output=True, text=True).stdout.strip()

    # -- running the program ----------------------------------------------

    def env(self):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("SHOPIFY_", "GIT_", "PNPM_", "SPEED_TUNE_"))}
        env.update({
            "PATH": str(FAKES) + os.pathsep + env.get("PATH", ""),
            "FAKE_STORE": str(self.store_file),
            "FAKE_DEFAULTS": str(self.root / "defaults"),
            "SPEED_TUNE_LOCK": str(self.lock),
            "SPEED_TUNE_POLL_SECONDS": "0",
            "TMPDIR": str(self.tmp),
            "HOME": str(self.root / "home"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
        })
        return env

    def run(self, *args, cwd=None, env=None):
        completed = subprocess.run(
            [sys.executable, str(PROGRAM), *[str(a) for a in args]],
            cwd=cwd or self.repo, env=dict(self.env(), **(env or {})), capture_output=True,
            text=True, stdin=subprocess.DEVNULL, timeout=120)
        return Result(completed)

    def publish_repo(self, repo=None):
        """Make the published theme hold the repo's theme files, as on a store whose
        live theme is the repo's main branch. A file that is not UTF-8 is kept the way
        the fake CLI reads it."""
        root = Path(repo) if repo else self.repo
        files = {}
        for folder in THEME_FOLDERS:
            for path in sorted((root / folder).rglob("*")):
                if path.is_file():
                    files[path.relative_to(root).as_posix()] = path.read_bytes().decode(
                        "utf-8", "surrogateescape")
        self.edit_store(lambda s: s.setdefault("files", {}).update({str(LIVE_THEME): files}))

    def theme_files(self, theme_id):
        """The files the fake store holds for one theme: {path: text}."""
        return self.store().get("files", {}).get(str(theme_id), {})

    def pushes(self):
        """Every `theme push` the program made: [{theme, only, ignore}]."""
        return self.store().get("pushes", [])

    def start(self, *extra, cwd=None):
        """Start an invocation that is expected to succeed; return its theme ids."""
        self.publish_repo(cwd)
        result = self.run("start", "--store", STORE_URL, *extra, cwd=cwd)
        self.test.assertEqual(result.code, 0, result)
        themes = dict(re.findall(r"^START theme=(\w+) id=(\d+)", result.out, re.M))
        return {name: int(theme_id) for name, theme_id in themes.items()}, result
