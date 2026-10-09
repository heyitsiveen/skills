"""pages: propose the collection and product pages to measure, or set them.

With no flags it proposes, reading the published storefront: the first
collection in the header's main navigation, and the first available product in
the store's best-selling order. The developer confirms them at the plan stop;
--collection and --product set a page by its path, until the plan is approved.
Home is always `/`.
"""

import json
import re
from urllib.parse import urlsplit

from tuner import ledger, stats, storefront
from tuner.output import Failed, Refused, say

ORDER = 20
SKIPPED_COLLECTIONS = ("all", "vendors", "types", "frontpage")
CANDIDATES = 8


def register(sub):
    p = sub.add_parser("pages", help="propose the collection and product pages, or set them")
    p.add_argument("--collection", metavar="PATH", help="set the collection page, e.g. /collections/sale")
    p.add_argument("--product", metavar="PATH", help="set the product page, e.g. /products/mug")
    p.set_defaults(run=run)


def run(args):
    inv = ledger.current("pages")
    if (inv.data.get("plan") or {}).get("approved_at"):
        raise Refused("plan-approved", "the plan approved at %s was measured on these pages, so "
                      "they stay" % inv.data["plan"]["approved_at"])
    pages = inv.data.setdefault("pages", {"home": "/"})
    store_url = inv.store_url
    sources = {}
    if args.collection or args.product:
        for page, path in (("collection", args.collection), ("product", args.product)):
            if path:
                pages[page] = checked_path(page, path)
                sources[page] = "set by the developer"
    else:
        pages["collection"] = propose_collection(store_url)
        sources["collection"] = "first collection in the main navigation"
        pages["product"] = propose_product(store_url)
        sources["product"] = "first available product in best-selling order"
    for page, source in sources.items():
        inv.log("pages", "%s page %s (%s)" % (page, pages[page], source))
    inv.save()
    for page in stats.PAGE_ORDER:
        if page in pages:
            say("PAGE", page, inv.page_url(page), "(%s)" % sources[page] if page in sources else "")
    return 0


def checked_path(page, path):
    value = urlsplit(path).path if "://" in path else path.split("?")[0].split("#")[0]
    kind = "collections" if page == "collection" else "products"
    if not re.fullmatch(r"/%s/[^/]+" % kind, value):
        raise Refused("bad-page", "%r is not a /%s/<handle> path" % (path, kind))
    return value


def local_path(href, host):
    """A link as a bare storefront path: same host only, no locale, query or fragment."""
    parts = urlsplit(href.replace("&amp;", "&"))
    if parts.hostname and parts.hostname.lower() != host:
        return None
    path = parts.path or ""
    path = re.sub(r"^/[a-z]{2}(?:-[a-z]{2,4})?(?=/(?:collections|products)/)", "", path)
    return path.rstrip("/") or None


def hrefs(html):
    return re.findall(r"""href\s*=\s*["']([^"']+)["']""", html)


def navigation(html):
    """The header's main navigation, falling back to the header, then to all before <main>."""
    for pattern in (r"<nav\b[^>]*class=\"[^\"]*\bheader__nav\b[^\"]*\"[^>]*>(.*?)</nav>",
                    r"<header\b[^>]*>(.*?)</header>"):
        found = re.search(pattern, html, re.S | re.I)
        if found:
            return found.group(1)
    return html.split("<main", 1)[0]


def main_region(html):
    found = re.search(r"<main\b[^>]*>(.*?)</main>", html, re.S | re.I)
    return found.group(1) if found else ""


def propose_collection(store_url):
    host = urlsplit(store_url).hostname
    home = storefront.fetch(store_url)
    for href in hrefs(navigation(home.body)):
        path = local_path(href, host)
        m = re.fullmatch(r"/collections/([^/]+)", path or "")
        if m and m.group(1) not in SKIPPED_COLLECTIONS:
            return path
    raise Failed("no-collection", "the main navigation on %s links no collection" % store_url,
                 "Ask the developer for the collection page and pass it with --collection.")


def propose_product(store_url):
    host = urlsplit(store_url).hostname
    listing = storefront.fetch(store_url + "collections/all?sort_by=best-selling")
    seen = []
    for href in hrefs(main_region(listing.body)):
        path = local_path(href, host) or ""
        m = re.search(r"(?:^|/)products/([^/]+)$", path)
        if m and "/products/" + m.group(1) not in seen:
            seen.append("/products/" + m.group(1))
    for path in seen[:CANDIDATES]:
        product = storefront.fetch(store_url + path.lstrip("/") + ".js")
        try:
            available = product.status == 200 and json.loads(product.body).get("available")
        except ValueError:
            available = False
        if available:
            return path
    raise Failed("no-product", "no available product in %scollections/all?sort_by=best-selling"
                 % store_url, "Ask the developer for the product page and pass it with --product.")
