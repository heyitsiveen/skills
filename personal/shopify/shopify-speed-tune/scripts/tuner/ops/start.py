"""start: open an invocation for one store from inside its theme repo.

Refuses, changing nothing, when the store is not the repo's, when another
invocation is unfinished on this machine, or when the theme library has no
room for two themes. Then it takes the machine lock, opens the ledger, creates
the invocation's branch, duplicates the published theme into the Working theme
and the Control theme, downloads Chrome for Testing and pins Lighthouse.

Each thing it creates is written to the ledger the moment it exists, so a
failure part-way leaves a ledger that `finish --discard` can clean up from.
"""

import os
import tempfile
import time
from datetime import datetime

from tuner import ledger, lock, repo, shopify, storefront, tools
from tuner.output import Failed, Refused, Stop, say

ORDER = 10
THEME_LIMIT = 20


def register(sub):
    p = sub.add_parser("start", help="check the store and the machine, then open an invocation")
    p.add_argument("--store", required=True, help="the store's public URL, e.g. https://example.com/")
    p.add_argument("--score", type=int, default=80,
                   help="the requested Performance score, 1-100 (default 80)")
    p.add_argument("--theme-limit", type=int, default=THEME_LIMIT,
                   help="themes the store's plan allows (default 20; Shopify Plus allows 100)")
    p.set_defaults(run=run)


def run(args):
    if not 1 <= args.score <= 100:
        raise Refused("bad-score", "the requested score must be 1-100, not %d" % args.score)
    store_url = storefront.base_url(args.store)
    root = repo.root()
    repo.require_theme(root)
    configured = repo.configured_store(root)
    lock.refuse_if_held()

    shop = storefront.shop(store_url)
    actual = repo.myshopify(shop["myshopify_domain"])
    if actual != configured:
        raise Refused("store-mismatch",
                      "%s is %s, but this repo's shopify.theme.toml names %s"
                      % (store_url, actual, configured),
                      "Run from the theme repo of the store you mean, or pass that store's URL.")
    public = storefront.base_url(shop.get("url") or shop.get("domain") or store_url)

    repo.require_clean(root)
    start_branch = repo.current_branch(root)
    library = shopify.themes(configured)
    published = live_theme(library)
    counted = [t for t in library if t.get("role") != "development"]
    if len(counted) + 2 > args.theme_limit:
        raise Refused("no-theme-room",
                      "the theme library holds %d of %d themes, so two more do not fit"
                      % (len(counted), args.theme_limit),
                      "Ask the developer to free two slots; this skill never deletes a theme "
                      "to make room. On Shopify Plus, pass --theme-limit 100.")
    served = storefront.fetch(public).served_theme()
    if served != published["id"]:
        raise Refused("store-cli-mismatch",
                      "%s serves theme %s, but the CLI's published theme for %s is %s"
                      % (public, served, configured, published["id"]))

    invocation_id = new_id(root)
    workspace = tempfile.mkdtemp(prefix="shopify-speed-tune-%s-" % invocation_id)
    folder = ledger.folder_for(root, invocation_id)
    lock.acquire({"invocation": invocation_id, "store": public, "repo": root,
                  "ledger": os.path.join(folder, "ledger.json"), "workspace": workspace})
    inv = ledger.create(root, invocation_id, {
        "state": "open",
        "requested_score": args.score,
        "store": {"url": public, "myshopify": configured, "name": shop.get("name"),
                  "published_theme": {"id": published["id"], "name": published.get("name")}},
        "repo": {"root": root, "start_branch": start_branch, "start_commit": repo.head(root)},
        "workspace": workspace,
        "tools": {},
        "themes": {},
        "pages": {"home": "/"},
        "samples": [],
    })
    if repo.exclude_from_git(root):
        say("NOTE", ".agent/ added to .git/info/exclude")
    say("START", "invocation=%s" % invocation_id, "ledger=%s" % inv.path)
    say("START", "store=%s" % public, "myshopify=%s" % configured,
        "published=%s" % published["id"])

    try:
        prepare(inv, configured, published)
    except Stop as failure:
        inv.log("start", "failed: %s" % failure)
        inv.save()
        failure.notes = failure.notes + (
            "Run `finish --discard` to remove what start created and release the lock.",)
        raise
    say("START ready")
    return 0


def prepare(inv, store, published):
    data, root, workspace = inv.data, inv.data["repo"]["root"], inv.data["workspace"]

    data["tools"]["chrome_preferences"] = tools.save_chrome_preferences(workspace)
    branch = "speed-tune/" + inv.id
    repo.create_branch(root, branch)
    data["repo"]["branch"] = branch
    inv.log("start", "created branch %s" % branch)
    inv.save()
    say("START", "branch=%s" % branch)

    for role in ("working", "control"):
        name = "speed-tune %s %s" % (inv.id, role)
        created = shopify.duplicate(store, published["id"], name)
        data["themes"][role] = {"id": created["id"], "name": created["name"]}
        inv.log("start", "duplicated %s into the %s theme %s" % (published["id"], role, created["id"]))
        inv.save()
        say("START", "theme=%s" % role, "id=%s" % created["id"], 'name="%s"' % created["name"])
    for role in ("working", "control"):
        theme = data["themes"][role]
        wait_until_processed(store, theme["id"])
        cookie = storefront.preview_cookie(data["store"]["url"], theme["id"])
        theme["asset_path"] = storefront.verify_theme(data["store"]["url"], cookie, theme["id"])
        inv.save()
        say("START", "preview=%s" % role, "assets=%s" % theme["asset_path"])

    chrome = tools.install_chrome(workspace)
    data["tools"]["chrome"] = {"build": tools.CHROME_BUILD, "path": chrome}
    inv.save()
    say("START", "chrome=%s" % tools.CHROME_BUILD)
    data["tools"]["lighthouse"] = tools.pin_lighthouse(workspace)
    inv.log("start", "pinned lighthouse %s and chrome %s" % (tools.LIGHTHOUSE, tools.CHROME_BUILD))
    inv.save()
    say("START", "lighthouse=%s" % data["tools"]["lighthouse"])


def live_theme(library):
    live = [t for t in library if t.get("role") == "live"]
    if len(live) != 1:
        raise Failed("no-published-theme", "the store lists %d published themes" % len(live))
    return {"id": int(live[0]["id"]), "name": live[0].get("name")}


def new_id(root):
    base = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate, n = base, 1
    while os.path.exists(ledger.folder_for(root, candidate)) or \
            repo.branch_exists(root, "speed-tune/" + candidate):
        n += 1
        candidate = "%s-%d" % (base, n)
    return candidate


def wait_until_processed(store, theme_id, limit=600):
    pause = float(os.environ.get("SPEED_TUNE_POLL_SECONDS", "5"))
    deadline = time.monotonic() + limit
    while True:
        found = shopify.theme(store, theme_id)
        if found is None:
            raise Failed("theme-missing", "theme %s vanished after it was duplicated" % theme_id)
        if not found.get("processing"):
            return
        if time.monotonic() > deadline:
            raise Failed("theme-processing", "theme %s was still processing after %d s"
                         % (theme_id, limit))
        time.sleep(pause)
