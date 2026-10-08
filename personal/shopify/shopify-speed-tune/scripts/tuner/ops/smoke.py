"""smoke: compare the Working theme with the Control theme on the three pages.

The smoke checker loads each page on both themes and records whether its
checks pass, which app blocks are present, and which console errors and Liquid
errors appear. The program records those results under a label and judges
them differentially, printing one SMOKE line per finding and a result line.

--results records an existing results file instead of running the checker:
the same checks and judgement, no browser.

While a Round is open, the check belongs to it: its label is the Round's, and
it runs only once the Working theme holds the Round's change as the tree has it.
"""

import json
import os

from tuner import clock, ledger, rounds, smoke, storefront
from tuner.output import Failed, Refused, say

ORDER = 40


def register(sub):
    p = sub.add_parser("smoke", help="compare the Working theme with the Control theme on the three pages")
    p.add_argument("--label",
                   help="what the results belong to (default: the open Round, else baseline)")
    p.add_argument("--results", metavar="FILE",
                   help="record this smoke-checker results file instead of running the checker")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("smoke")
    rnd = rounds.current(inv)
    if rnd is not None:
        if args.label not in (None, rounds.label(rnd["n"])):
            raise Refused("round-open", "Round %d is open, so the smoke check is its own, not %s"
                          % (rnd["n"], args.label))
        rounds.require_measurable(inv, rnd)
        args.label = rounds.label(rnd["n"])
    args.label = args.label or "baseline"
    if any(record["label"] == args.label for record in inv.data.get("smoke", [])):
        raise Refused("smoke-recorded", "the smoke check %s already has its result" % args.label,
                      "A label takes one result, so a failed check is never retried into a pass.")
    themes = {role: theme(inv, role)["id"] for role in smoke.ROLES}
    urls = {page: storefront.preview_url(inv.page_url(page)) for page in smoke.PAGES}
    if args.results:
        with open(args.results, encoding="utf-8") as f:
            results = json.load(f)
        source, stop = "file", Refused
    else:
        results = check(inv, urls, themes)
        source, stop = "checker", Failed
    pages = results.get("pages") or {}
    smoke.validate(pages, themes, urls, stop=stop)
    inv.data.setdefault("smoke", []).append({
        "label": args.label, "taken_at": clock.now(), "source": source,
        "browser": results.get("browser"), "pages": pages})
    inv.log("smoke", "%s results recorded" % args.label)
    inv.save()
    for page in smoke.PAGES:
        for role in smoke.ROLES:
            say("SMOKE", smoke.page_line(args.label, page, role, pages[page][role]))
    judgement = smoke.judge(pages)
    for line in judgement.lines(args.label):
        say("SMOKE", line)
    say("SMOKE", smoke.result_line(args.label, judgement))
    return 0


def check(inv, urls, themes):
    """Run the smoke checker, after reading back that each theme's cookie previews it."""
    data = inv.data
    workspace = data["workspace"]
    chrome = data["tools"].get("chrome", {}).get("path", "")
    if not os.access(chrome, os.X_OK):
        raise Refused("no-chrome", "the invocation's Chrome is missing at %r" % chrome,
                      "It is downloaded by `start`; a finished invocation has none.")
    store_url = data["store"]["url"]
    cookies = {}
    for role in smoke.ROLES:
        found = theme(inv, role)
        cookies[role] = storefront.preview_cookie(store_url, found["id"])
        served = storefront.verify_theme(urls["home"], cookies[role], found["id"])
        if found.get("asset_path") and served != found["asset_path"]:
            raise Failed("preview-changed", "theme %s now serves %s, not %s"
                         % (found["id"], served, found["asset_path"]))
    return smoke.run_checker(workspace, chrome, store_url, urls, themes, cookies)


def theme(inv, role):
    found = inv.data["themes"].get(role)
    if not found or found.get("deleted"):
        raise Refused("no-theme", "the invocation has no %s theme" % role)
    return found
