"""The smoke check: does each page still work on the Working theme as it does on the Control theme?

The smoke checker (browser/smoke.mjs) loads the three pages on both themes and
records what it saw: its checks, the app blocks present, console errors and
Liquid error text. This module keeps those results and judges them
differentially, so a store's existing quirks never count against a change.
"""

import json
import os
import re
from collections import Counter

from tuner import browser, stats
from tuner.output import Failed, Refused

ROLES = ("control", "working")


def run_checker(workspace, chrome_binary, store_url, urls, themes, cookies, timeout=900):
    """Run the smoke checker on both themes in a fresh copy of the invocation's Chrome.

    `urls` maps each page to the URL it loads from, `themes` each role to its
    theme id and `cookies` each role to its preview cookie. The cookies reach
    the checker on stdin and are cut from its results before they are returned.
    """
    spec = os.path.join(workspace, "smoke-spec.json")
    out = os.path.join(workspace, "smoke-results.json")
    with open(spec, "w", encoding="utf-8") as f:
        json.dump({"store": store_url, "pages": urls, "themes": themes}, f)
    try:
        with browser.Chrome(workspace, chrome_binary) as chrome:
            proc = browser.node(workspace, "smoke.mjs", "--port", str(chrome.port), "--spec", spec,
                                "--out", out, stdin=json.dumps(cookies), timeout=timeout)
        if proc.returncode != 0 or not os.path.isfile(out):
            raise Failed("smoke-checker", "the smoke checker stopped: %s"
                         % browser.last_line(proc.stderr or proc.stdout))
        with open(out, encoding="utf-8") as f:
            text = f.read()
    finally:
        for path in (spec, out):
            if os.path.exists(path):
                os.remove(path)
    for cookie in cookies.values():
        text = text.replace(cookie.split("=", 1)[1], "<removed>")
    return json.loads(text)


class Judgement:
    """The findings against the Working theme, in page order, each one SMOKE line."""

    def __init__(self):
        self.findings = []  # (kind, line)

    @property
    def passed(self):
        return not self.findings

    def count(self, kind):
        return sum(1 for found, _ in self.findings if found == kind)

    def lines(self, label):
        return ["%s %s" % (label, line) for _, line in self.findings]


MISSING = {"status": "missing", "detail": "the check did not run"}


def recorded(data, label):
    """The results the ledger `data` holds under `label`, or None. The ledger keeps what the
    checker saw, never a verdict on it: every reader judges them by the rule in force."""
    return next((r for r in data.get("smoke", []) if r["label"] == label), None)


def judge(pages):
    """Every way the Working theme does worse than the Control theme, page by page.

    A check counts only when it passes on the Control theme and does not pass
    on the Working theme; an error counts only when the Control theme lacks it;
    an app block counts when the Control theme has it and the Working theme not,
    each block known by its key (app_block_key), each copy of a key counted.
    """
    judgement = Judgement()
    for page in stats.PAGE_ORDER:
        control, working = pages[page]["control"], pages[page]["working"]
        for name, check in control["checks"].items():
            theirs = working["checks"].get(name, MISSING)
            if check.get("status") == "pass" and theirs.get("status") != "pass":
                detail = theirs.get("detail")
                judgement.findings.append(("regression", "%s regression %s: control %s, working %s%s" % (
                    page, name, check.get("status"), theirs.get("status"),
                    " (%s)" % detail if detail else "")))
        known = {error_key(e) for e in control.get("console_errors") or []}
        for error in unique(working.get("console_errors") or []):
            if error_key(error) not in known:
                judgement.findings.append(("new error", "%s new-error console: %s%s" % (
                    page, error.get("text"), " (%s)" % error["url"] if error.get("url") else "")))
        known = {same_error(text) for text in control.get("liquid_errors") or []}
        for text in unique_texts(working.get("liquid_errors") or []):
            if same_error(text) not in known:
                judgement.findings.append(("new error", "%s new-error liquid: %s" % (page, text)))
        present = Counter(app_block_key(block) for block in working.get("app_blocks") or [])
        for block in control.get("app_blocks") or []:
            if present[app_block_key(block)]:
                present[app_block_key(block)] -= 1
            else:
                judgement.findings.append(("missing app block", "%s missing-app-block: %s"
                                           % (page, block)))
    return judgement


# An app block's element id is `shopify-block-<token>__<key>`. The token is
# Shopify's own and differs between two duplicates of one theme: a section's app
# block gets a different one on each copy. The key is the block's: the app's
# handle, the block's handle and the suffix the theme editor gave that instance,
# or an app embed's id. So the same block on both themes shares its key alone.
APP_BLOCK_ID = re.compile(r"shopify-block-.+?__(.+)")


def app_block_key(block):
    """What identifies an app block on any copy of its theme: its id after the token, or the
    whole id (or class) when it has no token."""
    found = APP_BLOCK_ID.fullmatch(block)
    return found.group(1) if found else block


# What may differ between two themes' copies of the same error: each theme's own
# asset folder, asset versions and other query strings, long numbers such as
# ids, and the line a Liquid error names once the change has moved it.
SAME_ERROR = (
    (re.compile(r"/cdn/shop/t/\d+/"), "/cdn/shop/t/<n>/"),
    (re.compile(r"\?[^\s\"')]*"), ""),
    (re.compile(r"\bline \d+"), "line <n>"),
    (re.compile(r"\d{4,}"), "<n>"),
    (re.compile(r"\s+"), " "),
)


def same_error(text):
    for pattern, replacement in SAME_ERROR:
        text = pattern.sub(replacement, text)
    return text.strip()


def error_key(error):
    return (same_error(error.get("text") or ""), same_error(error.get("url") or ""))


def unique(errors):
    seen, out = set(), []
    for error in errors:
        if error_key(error) not in seen:
            seen.add(error_key(error))
            out.append(error)
    return out


def unique_texts(texts):
    seen, out = set(), []
    for text in texts:
        if same_error(text) not in seen:
            seen.add(same_error(text))
            out.append(text)
    return out


def validate(pages, themes, urls, stop=Refused):
    """Raise `stop` unless the results cover both themes on the three pages, each
    page loaded from its URL, and it and every later same-origin response
    rendered by its own theme.

    `themes` maps each role to its theme id and `urls` each page to its URL. A
    page the store rendered with another theme lost its preview cookie: it says
    nothing about the change.
    """
    for page in stats.PAGE_ORDER:
        for role in ROLES:
            run = (pages.get(page) or {}).get(role)
            if not isinstance(run, dict) or not isinstance(run.get("checks"), dict):
                raise stop("smoke-results-invalid", "the results hold no %s run on the %s theme"
                           % (page, role))
            if run.get("url") != urls[page]:
                raise stop("smoke-wrong-page", "the %s page on the %s theme was loaded from %s, not %s"
                           % (page, role, run.get("url"), urls[page]))
            loaded = (run["checks"].get("load") or {}).get("status") == "pass"
            if loaded and run.get("theme") is None:
                raise stop("smoke-wrong-theme", "the %s page on the %s theme loaded but named no "
                           "theme" % (page, role))
            rendered = [run.get("theme")] + [int(t) if str(t).isdigit() else t
                                             for t in (run.get("served_by") or {})]
            other = next((t for t in rendered if t is not None and t != themes[role]), None)
            if other is not None:
                raise stop("smoke-wrong-theme", "the %s page on the %s theme was rendered by theme "
                           "%s, not %s" % (page, role, other, themes[role]),
                           "Its preview cookie was lost or refused; run the smoke check again.")


def page_line(label, page, role, run):
    checks = " | ".join("%s %s" % (name, check.get("status")) for name, check in run["checks"].items())
    return "%s %s %s theme=%s | %s | app-blocks %d | console-errors %d | liquid-errors %d" % (
        label, page, role, run.get("theme"), checks, len(run.get("app_blocks") or []),
        len(run.get("console_errors") or []), len(run.get("liquid_errors") or []))


def counted(n, noun):
    return "%d %s%s" % (n, noun, "" if n == 1 else "s")


def result_line(label, judgement):
    if judgement.passed:
        return "%s result pass" % label
    counts = [counted(judgement.count(kind), kind)
              for kind in ("regression", "new error", "missing app block") if judgement.count(kind)]
    return "%s result fail: %s" % (label, ", ".join(counts))
