"""The invocation's Chrome, started for one job and stopped by its pid.

Samples and the smoke checker both load pages the store renders with an
unpublished theme. Each job gets a fresh Chrome for Testing with a throwaway
profile inside the invocation's workspace and a debugging port. The theme's
preview cookie goes into that Chrome's cookie jar for the store's host only, so
it travels with every request to the store and with nothing else, and a cookie
the page sets later joins it rather than replacing it. Lighthouse and the smoke
checker then drive the same Chrome through the port.

    with Chrome(workspace, binary) as chrome:
        chrome.put_preview_cookie(store_url, cookie)
        ... lighthouse --port=chrome.port ...

Chrome runs in a process group of its own and is stopped by that group, never
by name, so the developer's other browsers and sessions keep running. The
cookie reaches the Node helpers on stdin, never on a command line.
"""

import os
import shutil
import signal
import subprocess
import tempfile
import time

from tuner import tools
from tuner.output import Failed
from tuner.proc import require

NODE_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "browser")

# The flags chrome-launcher 1.2.2 gives every Chrome it starts for Lighthouse
# (dist/flags.js), so a Sample runs in the browser Lighthouse would have started.
LAUNCHER_FLAGS = (
    "--disable-features=Translate,OptimizationHints,MediaRouter,DialMediaRouteProvider,"
    "CalculateNativeWinOcclusion,InterestFeedContentSuggestions,"
    "CertificateTransparencyComponentUpdater,AutofillServerCommunication,"
    "PrivacySandboxSettings4,RenderDocument",
    "--disable-extensions",
    "--disable-component-extensions-with-background-pages",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-client-side-phishing-detection",
    "--disable-sync",
    "--metrics-recording-only",
    "--disable-default-apps",
    "--mute-audio",
    "--no-default-browser-check",
    "--no-first-run",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-background-timer-throttling",
    "--disable-ipc-flooding-protection",
    "--password-store=basic",
    "--use-mock-keychain",
    "--force-fieldtrials=*BackgroundTracing/default/",
    "--disable-hang-monitor",
    "--disable-prompt-on-repost",
    "--disable-domain-reliability",
    "--propagate-iph-for-testing",
)


class Chrome:
    def __init__(self, workspace, binary, wait=30):
        self.workspace = workspace
        self.binary = binary
        self.wait = wait
        self.proc = None
        self.profile = None
        self.port = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()

    def start(self):
        if not os.access(self.binary, os.X_OK):
            raise Failed("no-chrome", "the invocation's Chrome is missing at %r" % self.binary)
        profiles = os.path.join(self.workspace, "profiles")
        os.makedirs(profiles, exist_ok=True)
        self.profile = tempfile.mkdtemp(prefix="chrome-", dir=profiles)
        argv = [self.binary, *LAUNCHER_FLAGS, "--headless=new",
                "--user-data-dir=" + self.profile, "--remote-debugging-port=0", "about:blank"]
        self.proc = subprocess.Popen(argv, env=tools.pnpm_env(self.workspace),
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
        self.port = self._debugging_port()

    def _debugging_port(self):
        """Chrome picks a free port and writes it to DevToolsActivePort in its profile."""
        marker = os.path.join(self.profile, "DevToolsActivePort")
        deadline = time.monotonic() + self.wait
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                code = self.proc.returncode
                self.stop()
                raise Failed("chrome-start", "Chrome for Testing exited with %s before opening "
                             "its debugging port" % code)
            try:
                with open(marker, encoding="utf-8") as f:
                    first = f.readline().strip()
            except OSError:
                first = ""
            if first.isdigit():
                return int(first)
            time.sleep(0.1)
        self.stop()
        raise Failed("chrome-start", "Chrome for Testing opened no debugging port within %d s"
                     % self.wait)

    def stop(self):
        """Kill Chrome's process group and delete its profile. Safe to call twice."""
        if self.proc is not None:
            # A leader that was never reaped still owns its pid, so the group
            # cannot belong to anyone else; one already reaped is left alone.
            if self.proc.returncode is None:
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except OSError:
                    pass
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            self.proc = None
        if self.profile:
            for _ in range(5):
                shutil.rmtree(self.profile, ignore_errors=True)
                if not os.path.exists(self.profile):
                    break
                time.sleep(0.2)
            self.profile = None

    def put_preview_cookie(self, store_url, cookie):
        """Put `_shopify_essential=<value>` in the default context's jar, for the store's host."""
        proc = node(self.workspace, "jar.mjs", "--port", str(self.port), "--store", store_url,
                    stdin=cookie + "\n", timeout=60)
        if proc.returncode != 0 or not proc.stdout.startswith("JAR "):
            raise Failed("preview-jar", "the preview cookie did not reach Chrome's cookie jar: %s"
                         % last_line(proc.stderr or proc.stdout))


def node(workspace, script, *args, stdin="", timeout=120):
    """Run one of the Node helpers beside this package, on the workspace's puppeteer-core."""
    require("node")
    env = tools.pnpm_env(workspace, SPEED_TUNE_NODE_PROJECT=tools.node_project(workspace))
    try:
        return subprocess.run(["node", os.path.join(NODE_SCRIPTS, script), *args],
                              input=stdin, env=env, cwd=workspace, capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Failed("timeout", "`node %s` did not finish within %d s" % (script, timeout))


def last_line(text):
    lines = [line for line in (text or "").strip().splitlines() if line.strip()]
    return lines[-1][:300] if lines else "no output"
