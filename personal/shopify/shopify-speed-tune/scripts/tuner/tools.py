"""The invocation's own tools: a test copy of Chrome and one pinned Lighthouse.

Both run through pnpm's on-demand runner with the pnpm store and cache pointed
inside the invocation's temp workspace, so nothing is installed globally and
cleanup is one folder removal. The developer's own browser never runs a Sample.

The versions are pinned together: Chrome for Testing 154.0.8037.57 is the
build puppeteer-core 25.12.0 pins, and Lighthouse 13.5.0 depends on that same
puppeteer-core, so one download serves Lighthouse, the jar helper and the smoke
checker. Lighthouse 13 is the major version PageSpeed Insights runs.
"""

import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import tempfile
from xml.parsers.expat import ExpatError

from tuner.output import Failed
from tuner.proc import child_env, run

LIGHTHOUSE = "13.5.0"
CHROME_BUILD = "154.0.8037.57"
CHROME_MAJOR = CHROME_BUILD.split(".")[0]
BROWSERS_CLI = "@puppeteer/browsers@3.2.3"
PUPPETEER = "25.12.0"
CFT_DOMAIN = "com.google.chrome.for.testing"


def pnpm_env(workspace, **extra):
    """The environment every pnpm child gets: an isolated store and cache.

    BREAKPAD_DUMP_LOCATION moves Chrome's crash database into the workspace;
    without it every launch writes under ~/Library/Application Support.
    """
    return child_env(
        PNPM_CONFIG_STORE_DIR=os.path.join(workspace, "pnpm", "store"),
        PNPM_CONFIG_CACHE_DIR=os.path.join(workspace, "pnpm", "cache"),
        PNPM_CONFIG_UPDATE_NOTIFIER="false",
        PNPM_CONFIG_DLX_CACHE_MAX_AGE="10080",
        BREAKPAD_DUMP_LOCATION=os.path.join(workspace, "crashpad"),
        **extra)


def node_project(workspace):
    """The Node project in the workspace that holds puppeteer-core for the Node helpers."""
    return os.path.join(workspace, "node")


def install_puppeteer(workspace):
    """puppeteer-core for the jar helper and the smoke checker, into the workspace.

    It is an ordinary project dependency of a throwaway project inside the
    workspace, installed through the workspace's own pnpm store, so removing the
    workspace removes it.
    """
    project = node_project(workspace)
    os.makedirs(project, exist_ok=True)
    with open(os.path.join(project, "package.json"), "w", encoding="utf-8") as f:
        json.dump({"name": "speed-tune-browser", "private": True, "type": "module"}, f)
        f.write("\n")
    proc = run(["pnpm", "add", "--save-exact", "puppeteer-core@" + PUPPETEER],
               cwd=project, env=pnpm_env(workspace), timeout=600)
    installed = os.path.join(project, "node_modules", "puppeteer-core", "package.json")
    try:
        with open(installed, encoding="utf-8") as f:
            version = json.load(f).get("version")
    except (OSError, ValueError):
        version = None
    if proc.returncode != 0 or version != PUPPETEER:
        raise Failed("puppeteer-install", "puppeteer-core@%s did not install: %s"
                     % (PUPPETEER, (proc.stderr or proc.stdout).strip()[-300:]))
    return version


def install_chrome(workspace):
    target = os.path.join(workspace, "chrome")
    proc = run(["pnpm", "dlx", BROWSERS_CLI, "install", "chrome@" + CHROME_BUILD,
                "--path", target, "--format", "{{path}}"],
               cwd=workspace, env=pnpm_env(workspace), timeout=900)
    lines = proc.stdout.strip().splitlines()
    path = lines[-1].strip() if lines else ""
    if proc.returncode != 0 or not os.access(path, os.X_OK):
        raise Failed("chrome-download", "Chrome for Testing %s did not install: %s"
                     % (CHROME_BUILD, (proc.stderr or proc.stdout).strip()[-300:]))
    return path


def pin_lighthouse(workspace):
    proc = run(["pnpm", "dlx", "lighthouse@" + LIGHTHOUSE, "--version"],
               cwd=workspace, env=pnpm_env(workspace), timeout=600)
    version = proc.stdout.strip().splitlines()[-1].strip() if proc.stdout.strip() else ""
    if proc.returncode != 0 or version != LIGHTHOUSE:
        raise Failed("lighthouse-pin", "lighthouse@%s did not run: %s"
                     % (LIGHTHOUSE, (proc.stderr or proc.stdout).strip()[-300:]))
    return version


# Chrome for Testing records its own location in the user's preferences on every
# launch, headless included. The domain is saved here before the first launch,
# with a digest of what it held, and `finish` puts it back and reads it back, so
# the machine ends as it began. A machine without `defaults` (not a Mac) has no
# such domain.

def _defaults(*args):
    return subprocess.run(["defaults", *args], stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=60)


def _canonical(value):
    """A preferences value with its dictionaries in key order, so equal settings read alike."""
    if isinstance(value, dict):
        return sorted((str(key), _canonical(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _digest(path):
    """A digest of an exported domain's settings, however the file lays them out."""
    with open(path, "rb") as f:
        data = f.read()
    try:
        settings = repr(_canonical(plistlib.loads(data))).encode("utf-8")
    except (ValueError, ExpatError):  # a file plistlib cannot read is compared byte for byte
        settings = data
    return hashlib.sha256(settings).hexdigest()


def chrome_preferences_now():
    """The digest of Chrome for Testing's preferences now, or None while the domain does not
    exist."""
    with tempfile.TemporaryDirectory(prefix="speed-tune-defaults-") as folder:
        exported = os.path.join(folder, "now.plist")
        if _defaults("export", CFT_DOMAIN, exported).returncode != 0:
            return None
        return _digest(exported)


def save_chrome_preferences(workspace):
    """Chrome for Testing's preferences before its first launch: {saved, existed, file, digest}."""
    if shutil.which("defaults") is None:
        return {"saved": False}
    saved = os.path.join(workspace, "cft-preferences.plist")
    existed = _defaults("export", CFT_DOMAIN, saved).returncode == 0
    return {"saved": True, "existed": existed, "file": saved,
            "digest": _digest(saved) if existed else None}


def chrome_preferences_as_before(snapshot):
    """True when Chrome for Testing's preferences hold what the snapshot saved."""
    return chrome_preferences_now() == snapshot.get("digest")


def restore_chrome_preferences(snapshot):
    """Put the saved domain back, then read it back: True when this call changed it.

    Raises cleanup-incomplete when `defaults` refuses, or when the domain still
    differs from the snapshot, which then stays in the workspace for the next try.
    """
    if not snapshot or not snapshot.get("saved") or chrome_preferences_as_before(snapshot):
        return False
    argv = ("import", CFT_DOMAIN, snapshot["file"]) if snapshot["existed"] \
        else ("delete", CFT_DOMAIN)
    proc = _defaults(*argv)
    if proc.returncode != 0:
        said = [line for line in (proc.stderr or "").splitlines() if line.strip()]
        raise Failed("cleanup-incomplete", "Chrome for Testing's preferences were not put back: "
                     "`defaults %s %s` exited %d: %s" % (argv[0], CFT_DOMAIN, proc.returncode,
                                                        said[-1][:200] if said else "no output"),
                     "Run `finish` again; when it stops here twice, show the developer this line.")
    if not chrome_preferences_as_before(snapshot):
        raise Failed("cleanup-incomplete", "Chrome for Testing's preferences were not put back: "
                     "they still differ from before the invocation",
                     "Run `finish` again; when it stops here twice, show the developer this line.")
    return True
