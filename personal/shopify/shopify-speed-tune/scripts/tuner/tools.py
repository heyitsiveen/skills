"""The invocation's own tools: a test copy of Chrome and one pinned Lighthouse.

Both run through pnpm's on-demand runner with the pnpm store and cache pointed
inside the invocation's temp workspace, so nothing is installed globally and
cleanup is one folder removal. The developer's own browser never runs a Sample.

The two versions are pinned together: Chrome for Testing 154.0.8037.57 is the
build puppeteer-core 25.12.0 pins, and Lighthouse 13.5.0 depends on that same
puppeteer-core, so one download serves Lighthouse and the smoke checker.
Lighthouse 13 is the major version PageSpeed Insights runs.
"""

import os
import shutil
import subprocess
import sys

from tuner.output import Failed
from tuner.proc import child_env, run

LIGHTHOUSE = "13.5.0"
CHROME_BUILD = "154.0.8037.57"
CHROME_MAJOR = CHROME_BUILD.split(".")[0]
BROWSERS_CLI = "@puppeteer/browsers@3.2.3"
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
# launch, headless included. The domain is saved here before the first launch
# and put back by `finish`, so the machine ends as it began.

def save_chrome_preferences(workspace):
    if sys.platform != "darwin" or shutil.which("defaults") is None:
        return {"saved": False}
    saved = os.path.join(workspace, "cft-preferences.plist")
    proc = subprocess.run(["defaults", "export", CFT_DOMAIN, saved],
                          stdin=subprocess.DEVNULL, capture_output=True, text=True)
    return {"saved": True, "existed": proc.returncode == 0, "file": saved}


def restore_chrome_preferences(snapshot):
    """Put the saved domain back once; True when this call restored it."""
    if not snapshot or not snapshot.get("saved") or snapshot.get("restored") \
            or shutil.which("defaults") is None:
        return False
    if snapshot.get("existed"):
        if not os.path.isfile(snapshot["file"]):
            return False
        argv = ["defaults", "import", CFT_DOMAIN, snapshot["file"]]
    else:
        argv = ["defaults", "delete", CFT_DOMAIN]
    subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    snapshot["restored"] = True
    return True
