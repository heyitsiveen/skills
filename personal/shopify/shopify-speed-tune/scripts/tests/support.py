"""Scaffolding for the decision program's tests.

Each test gets a Sandbox: a throwaway client theme repo, a fake store behind
fake `shopify`, `curl` and `pnpm` executables placed first on the path, and its
own machine lock and temp dir. The program is driven only through its command
line, the way the skill drives it.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROGRAM = HERE.parent / "speed_tune.py"
FAKES = HERE / "fakes"
REPORTS = HERE / "fixtures" / "lighthouse"

STORE_URL = "https://store.example/"
MYSHOPIFY = "example-store.myshopify.com"
LIVE_THEME = 100
# The asset folder the fixtures' theme requests come from: /cdn/shop/t/23/.
CONTROL_ASSET_NUMBER = 23


def report(name):
    """Path of a real Lighthouse report fixture, by its file stem."""
    return REPORTS / (name + ".json")


def read_report(name):
    with open(report(name), encoding="utf-8") as f:
        return json.load(f)


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
    def __init__(self, test):
        self.test = test
        self.root = Path(tempfile.mkdtemp(prefix="speed-tune-test-"))
        test.addCleanup(shutil.rmtree, self.root, True)
        self.repo = self.root / "repo"
        self.tmp = self.root / "tmp"
        self.tmp.mkdir()
        self.lock = self.root / "machine" / "speed-tune.lock"
        self.store_file = self.root / "store.json"
        self.write_store(self.default_store())
        self.make_repo(self.repo)

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

    # -- client theme repos -----------------------------------------------

    def make_repo(self, path, store=MYSHOPIFY, toml=None):
        (path / "layout").mkdir(parents=True)
        (path / "config").mkdir()
        (path / "layout" / "theme.liquid").write_text("<html>{{ content_for_header }}</html>\n")
        (path / "config" / "settings_schema.json").write_text("[]\n")
        if toml is None:
            toml = '[environments.default]\nstore = "%s"\n' % store
        (path / "shopify.theme.toml").write_text(toml)
        self.git(path, "init", "-q", "-b", "main")
        self.git(path, "add", "-A")
        self.git(path, "commit", "-q", "-m", "init")
        with open(path / ".git" / "info" / "exclude", "a", encoding="utf-8") as f:
            f.write(".agent/\n")
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

    def run(self, *args, cwd=None):
        completed = subprocess.run(
            [sys.executable, str(PROGRAM), *[str(a) for a in args]],
            cwd=cwd or self.repo, env=self.env(), capture_output=True, text=True,
            stdin=subprocess.DEVNULL, timeout=120)
        return Result(completed)

    def start(self, *extra, cwd=None):
        """Start an invocation that is expected to succeed; return its theme ids."""
        result = self.run("start", "--store", STORE_URL, *extra, cwd=cwd)
        self.test.assertEqual(result.code, 0, result)
        themes = dict(re.findall(r"^START theme=(\w+) id=(\d+)", result.out, re.M))
        return {name: int(theme_id) for name, theme_id in themes.items()}, result
