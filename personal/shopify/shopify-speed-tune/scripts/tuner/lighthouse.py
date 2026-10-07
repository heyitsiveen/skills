"""Lighthouse reports: running the pinned Lighthouse, and reading what a report says.

A report becomes a Sample only when it is a clean measurement of the intended
page, device and theme: no runtime error, both category scores present, the
pinned Lighthouse and Chrome, the page it asked for with no redirect, the
theme's own asset folder among its requests, and exactly the blocked URL
patterns its Measurement asked for (none, except for a Ceiling Sample).
Anything else is rejected with a short reason, never recorded.
"""

import json
import os
import re
import shutil
import signal
import subprocess
import time

from tuner import tools
from tuner.proc import require

# The seven figures a Measurement reports, in report order.
METRICS = ("performance", "lcp", "tbt", "cls", "fcp", "si", "accessibility")
AUDITS = {
    "lcp": "largest-contentful-paint",
    "tbt": "total-blocking-time",
    "cls": "cumulative-layout-shift",
    "fcp": "first-contentful-paint",
    "si": "speed-index",
}
# Dropped before a report is kept: images, translations, and the request
# headers, which carry the preview cookie.
HEAVY_AUDITS = ("screenshot-thumbnails", "final-screenshot", "full-page-screenshot")


class Rejected(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def metrics(report):
    """The seven figures: scores as 0-100 integers, times in ms, CLS unitless."""
    out = {}
    for category in ("performance", "accessibility"):
        score = (report.get("categories", {}).get(category) or {}).get("score")
        if score is None:
            raise Rejected("no-score %s" % category)
        out[category] = int(round(score * 100))
    for name, audit_id in AUDITS.items():
        value = (report.get("audits", {}).get(audit_id) or {}).get("numericValue")
        if value is None:
            raise Rejected("no-metric %s" % audit_id)
        out[name] = float(value)
    return out


def check(report, url, device, pinned, asset_path=None, blocked=()):
    """Raise Rejected unless the report is a clean Sample of `url` on `device`,
    taken with exactly the `blocked` URL patterns (none for an ordinary Sample)."""
    error = report.get("runtimeError")
    if error:
        raise Rejected("runtime-error %s" % error.get("code", "unknown"))
    used = (report.get("configSettings") or {}).get("blockedUrlPatterns") or []
    if sorted(used) != sorted(blocked):
        raise Rejected("wrong-blocking %d patterns, not %d" % (len(used), len(blocked)))
    version = report.get("lighthouseVersion")
    if version != pinned:
        raise Rejected("wrong-lighthouse %s" % version)
    agent = (report.get("environment") or {}).get("hostUserAgent", "")
    if "HeadlessChrome/%s." % tools.CHROME_MAJOR not in agent:
        browser = re.search(r"\S*Chrome/[\d.]+", agent)
        raise Rejected("wrong-chrome %s" % (browser.group(0) if browser else "unknown"))
    form_factor = (report.get("configSettings") or {}).get("formFactor")
    if form_factor != device:
        raise Rejected("wrong-device %s" % form_factor)
    if report.get("requestedUrl") != url:
        raise Rejected("wrong-page %s" % report.get("requestedUrl"))
    if report.get("mainDocumentUrl") != url:
        raise Rejected("redirected %s" % report.get("mainDocumentUrl"))
    if asset_path:
        requests = (((report.get("audits") or {}).get("network-requests") or {})
                    .get("details") or {}).get("items") or []
        if not any(asset_path in (item.get("url") or "") for item in requests):
            raise Rejected("wrong-theme no request under %s" % asset_path)
    return metrics(report)


def keepable(report, secrets=()):
    """The report as it may be stored: no cookie, no screenshots, no translations."""
    kept = dict(report)
    kept.pop("i18n", None)
    kept.pop("fullPageScreenshot", None)
    settings = dict(kept.get("configSettings") or {})
    if settings.get("extraHeaders"):
        settings["extraHeaders"] = {name: "<removed>" for name in settings["extraHeaders"]}
    kept["configSettings"] = settings
    audits = dict(kept.get("audits") or {})
    for audit_id in HEAVY_AUDITS:
        audits.pop(audit_id, None)
    kept["audits"] = audits
    text = json.dumps(kept, ensure_ascii=False)
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<removed>")
    return text


def take(workspace, chrome, url, device, flags_file, output, timeout=300, blocked=()):
    """One Sample: the pinned Lighthouse through pnpm's on-demand runner, on the
    invocation's Chrome, with the theme's preview cookie in a flags file, and
    `blocked` URL patterns for a Ceiling Sample.

    The URL goes first: Lighthouse's array flags swallow any argument after them.
    Returns the parsed report, or raises Rejected.
    """
    require("pnpm")
    argv = ["pnpm", "dlx", "--silent", "lighthouse@" + tools.LIGHTHOUSE, url,
            "--cli-flags-path=" + flags_file,
            "--only-categories=performance,accessibility",
            "--output=json", "--output-path=" + output,
            "--chrome-flags=--headless=new",
            "--quiet", "--no-enable-error-reporting",
            "--skip-audits=bf-cache,modern-http-insight",
            "--disable-full-page-screenshot"]
    if device == "desktop":
        argv.append("--preset=desktop")
    argv += ["--blocked-url-patterns=" + pattern for pattern in blocked]
    env = tools.pnpm_env(workspace, CHROME_PATH=chrome)
    before = _launcher_profiles()
    proc = subprocess.Popen(argv, cwd=workspace, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            start_new_session=True)
    try:
        _, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_group(proc.pid)
        _kill_new_chrome(before, chrome)
        proc.communicate()
        raise Rejected("timeout after %d s" % timeout)
    if not os.path.isfile(output):
        raise Rejected("lighthouse-exit %d %s" % (proc.returncode, (err or "").strip()[-160:]))
    with open(output, encoding="utf-8") as f:
        report = json.load(f)
    if proc.returncode != 0 and not report.get("runtimeError"):
        raise Rejected("lighthouse-exit %d" % proc.returncode)
    return report


# chrome-launcher starts Chrome in its own process group, so killing Lighthouse
# leaves Chrome running. Its throwaway profile (lighthouse.XXXXXXX.*) holds the
# pid. Only a profile that appeared during this Sample, whose process runs this
# invocation's own Chrome binary, is killed: never a process found by name.

def _launcher_root():
    try:
        out = subprocess.run(["getconf", "DARWIN_USER_TEMP_DIR"], capture_output=True,
                             text=True, stdin=subprocess.DEVNULL).stdout.strip()
    except OSError:
        out = ""
    return out or "/tmp"


def _launcher_profiles():
    root = _launcher_root()
    try:
        return {n for n in os.listdir(root) if n.startswith("lighthouse.")}
    except OSError:
        return set()


def _kill_group(pid):
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        pass


def _runs(pid, binary):
    command = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True,
                             text=True, stdin=subprocess.DEVNULL).stdout
    return bool(binary) and binary in command


def _kill_new_chrome(before, chrome):
    root = _launcher_root()
    for name in _launcher_profiles() - before:
        try:
            with open(os.path.join(root, name, "chrome.pid"), encoding="utf-8") as f:
                pid = int(f.read().strip())
        except (OSError, ValueError):
            continue
        if not _runs(pid, chrome):
            continue
        _kill_group(pid)
        time.sleep(0.5)
        shutil.rmtree(os.path.join(root, name), ignore_errors=True)
