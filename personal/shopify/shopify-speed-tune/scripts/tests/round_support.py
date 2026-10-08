"""Shared set-up for the Round tests: a theme repo with real-shaped files, an
approved plan over it, a Round open, and pairs derived from the real reports.

Pairs are derived the way every fixture here is: a real report of the page,
with only its score fields edited. A Working theme Sample is that report as the
Working theme served it, so its requests come from the Working theme's own
asset folder.
"""

import atexit
import json
import shutil
import tempfile
from pathlib import Path

from plan_support import COLLECTION, PAGES, PRODUCT, diagnosed, write_items
from support import SMOKE_RESULTS, Sandbox, read_report

# The sandbox duplicates the published theme twice: the Working theme first.
WORKING, CONTROL = 200, 201
ASSET_FOLDERS = {"working": "/cdn/shop/t/22/", "control": "/cdn/shop/t/23/"}

LAZY = '<img src="{{ image | image_url: width: 800 }}" loading="lazy">\n'
EAGER = '<img src="{{ image | image_url: width: 800 }}" loading="eager" fetchpriority="high">\n'

THEME = {
    "snippets/image.liquid": LAZY,
    "assets/theme.js": "document.documentElement.classList.add('js');\n",
    # A vendored library that reads the user agent, as Golden's swiper bundle does.
    "assets/slider.js": "window.Slider = function () { return /Mobi/.test(navigator.userAgent); };\n",
    "templates/index.json": json.dumps({"sections": {"hero": {"type": "hero"}},
                                        "order": ["hero"]}, indent=2) + "\n",
    "sections/header-group.json": json.dumps({"type": "header", "name": "Header group",
                                              "sections": {}, "order": []}, indent=2) + "\n",
    "config/settings_data.json": json.dumps({"current": {"colors": "default"}}, indent=2) + "\n",
}

ITEMS = [
    {"change": "Load the hero image eagerly", "pages": ["home"],
     "cause": "the LCP image is lazy-loaded", "effect": "+5 to +10 on home"},
    {"change": "Drop the unused slider script", "pages": ["home", "collection", "product"],
     "cause": "slider.js is parsed on every page but no section uses it", "effect": "TBT -50 ms"},
]

PAGE_PATHS = {"home": "/", "collection": COLLECTION, "product": PRODUCT}


FROZEN = {}


def approved(test, items=ITEMS, *start_args, pre_commit=None):
    """An invocation over THEME whose plan of `items` the developer approved, started
    with `start_args` in a repo whose pre-commit hook is `pre_commit`.

    Reaching approval takes some thirty program runs, so it is done once per
    plan and kept as a copy; each test gets that copy put back at the same path,
    a fresh sandbox none of the other tests touched.
    """
    key = json.dumps([items, start_args, pre_commit])
    if key not in FROZEN:
        box = diagnosed(test, *start_args, theme_files=THEME, pre_commit=pre_commit)
        for args in (("plan", "--items", write_items(box, items)), ("plan", "--approve")):
            result = box.run(*args)
            test.assertEqual(result.code, 0, result)
        frozen = Path(tempfile.mkdtemp(prefix="speed-tune-frozen-"))
        shutil.copytree(box.root, frozen / "copy", symlinks=True)
        atexit.register(shutil.rmtree, frozen, True)
        FROZEN[key] = (box.root, frozen / "copy")
        return box
    root, frozen = FROZEN[key]
    return Sandbox.restored(test, root, frozen)


def opened(test, items=ITEMS, item="P1"):
    """`approved`, with a Round open for `item`."""
    box = approved(test, items)
    result = box.run("round", "--item", item)
    test.assertEqual(result.code, 0, result)
    return box


def write(box, path, text):
    target = box.repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


def apply_item(box, item):
    """Make plan item `item`'s change: P1 loads the hero eagerly, P2 drops the slider."""
    if item == "P1":
        write(box, "snippets/image.liquid", EAGER)
    else:
        (box.repo / "assets" / "slider.js").unlink()


def pushed(test, items=ITEMS, item="P1"):
    """`opened`, with the item's change made and pushed to the Working theme."""
    box = opened(test, items, item)
    apply_item(box, item)
    result = box.run("push")
    test.assertEqual(result.code, 0, result)
    return box


# Edits to the real smoke results, each making the Working theme do one thing worse.

def add_to_cart_fails(results):
    results["pages"]["product"]["working"]["checks"].update({
        "add-to-cart": {"status": "fail", "detail": "the cart still holds 0 item(s)"},
        "cart-count": {"status": "skip", "detail": "nothing was added"}})


def new_console_error(results):
    results["pages"]["home"]["working"]["console_errors"].append({
        "text": "Uncaught ReferenceError: Swiper is not defined",
        "url": "https://store.example/cdn/shop/t/22/assets/slider.js?v=172"})


def new_liquid_error(results):
    results["pages"]["product"]["working"]["liquid_errors"].append(
        "Liquid error (sections/main-product line 214): Could not find asset snippets/price.liquid")


def app_block_gone(results):
    results["pages"]["product"]["working"]["app_blocks"].remove(
        "shopify-block-AExampleBlock4Q__example_app_block_4")


def checked(box, change=None):
    """Record the Round's smoke check: the real results, with one change."""
    data = json.loads(SMOKE_RESULTS.read_text(encoding="utf-8"))
    if change:
        change(data)
    path = box.root / "smoke-results.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = box.run("smoke", "--results", path)
    box.test.assertEqual(result.code, 0, result)
    return result


def derived(box, page, n, theme, performance=None, accessibility=None):
    """The page's real mobile report n as `theme` served it, with scores edited."""
    data = read_report("%s-mobile-%d" % (page, n))
    for category, score in (("performance", performance), ("accessibility", accessibility)):
        if score is not None:
            data["categories"][category]["score"] = score / 100.0
    text = json.dumps(data).replace(ASSET_FOLDERS["control"], ASSET_FOLDERS[theme])
    path = box.root / ("%s-%d-%s-%s-%s.json" % (page, n, theme, performance, accessibility))
    path.write_text(text)
    return path


def scores(page):
    """The Performance and accessibility scores of the page's five real mobile reports."""
    out = []
    for n in range(1, 6):
        categories = read_report("%s-mobile-%d" % (page, n))["categories"]
        out.append((round(categories["performance"]["score"] * 100),
                    round(categories["accessibility"]["score"] * 100)))
    return out


def pair_files(box, page, gains, accessibility=0):
    """Five pairs on `page`: each Control Sample a real report, its Working Sample the
    same report with the Performance score moved by that pair's gain (and the
    accessibility score by `accessibility`)."""
    files = []
    for n, gain in enumerate(gains, 1):
        performance, a11y = scores(page)[n - 1]
        files.append((derived(box, page, n, "control"),
                      derived(box, page, n, "working", performance + gain, a11y + accessibility)))
    return files


def record_pairs(box, page, gains, accessibility=0):
    args = ["pairs", "--page", page]
    for control, working in pair_files(box, page, gains, accessibility):
        args += ["--pair", control, working]
    result = box.run(*args)
    box.test.assertEqual(result.code, 0, result)
    return result


NEUTRAL = (0, 0, 0, 0, 0)
# Per-pair Performance gains of the Working theme over the Control theme.
WIN_4 = (2, 2, 2, 2, -1)    # four wins, one loss
WIN_3 = (2, 2, 2, -1, -1)   # three wins
WIN_3_TIE_2 = (2, 2, 2, 0, 0)
LOSS_4 = (-1, -1, -1, -1, 0)
LOSS_3 = (-1, -1, -1, 0, 0)


def measure(box, gains=None, accessibility=None):
    """Record the Round's five pairs on every page; `gains` and `accessibility`
    map a page to its per-pair Performance gains and its accessibility change."""
    for page in PAGES:
        record_pairs(box, page, (gains or {}).get(page, NEUTRAL),
                     (accessibility or {}).get(page, 0))
