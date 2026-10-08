"""The Ceiling probe: which requests a Ceiling Sample blocks, and the check that it did.

The probe blocks every theme-owned request the first screen does not need:
theme scripts, theme fonts, and theme images other than the page's LCP image.
Stylesheets stay, because removing them changes what the first screen is, and
so does everything an app, a tag or Shopify itself loads.

Lighthouse passes the patterns to Chrome's Network.setBlockedURLs, which has no
allow-list: a '*' matches any run of characters, every pattern is implicitly
wrapped in '*', and a URL matching any pattern is blocked. So the probe is built
from what the page's baseline Samples requested: one broad pattern for each
class that cannot match an image (theme scripts and fonts by folder and
extension), one exact pattern per theme image path, and none at all for a path
the LCP image used. A pattern that would still match the LCP image is dropped.
"""

import html
import re
from urllib.parse import urlsplit

from tuner.lighthouse import Rejected

THEME_IMAGE_ROOT = "/cdn/shop/"
FONT_LIBRARY = "/cdn/fonts/"
FONT_CDN = "fonts.shopifycdn.com"
LAZY_CLASS = re.compile(r'\sclass="[^"]*\blazy(?:load|loaded|autosizes)\b')
LAZY_SOURCE = re.compile(r'\sdata-src(?:set)?="')


def matches(pattern, url):
    """Chrome's rule for a blocked-URL pattern (`urls` form, as Lighthouse sends it)."""
    position = 0
    for part in pattern.split("*"):
        found = url.find(part, position)
        if found < 0:
            return False
        position = found + len(part)
    return True


def requests(report):
    items = ((((report.get("audits") or {}).get("network-requests") or {})
              .get("details") or {}).get("items") or [])
    return [i for i in items if isinstance(i.get("url"), str)]


def _items(report, audit_id):
    audit = (report.get("audits") or {}).get(audit_id) or {}
    return (audit.get("details") or {}).get("items") or []


def _node(report):
    for audit_id in ("lcp-breakdown-insight", "lcp-discovery-insight"):
        for item in _items(report, audit_id):
            if isinstance(item, dict) and item.get("type") == "node":
                return item
    return None


def lcp(report):
    """The page's largest paint in one report.

    Returns {"kind": "image" | "text" | "none", "url": str | None, "selector": str | None}.
    An image whose URL cannot be recovered from the report has kind "image" and no url.
    """
    node = _node(report)
    selector = node.get("selector") if node else None
    table = next((i for i in _items(report, "lcp-breakdown-insight")
                  if isinstance(i, dict) and i.get("type") == "table"), None)
    if table is None:
        return {"kind": "none", "url": None, "selector": selector}
    subparts = {row.get("subpart") for row in table.get("items") or []}
    if not subparts & {"resourceLoadDelay", "resourceLoadDuration"}:
        return {"kind": "text", "url": None, "selector": selector}
    return {"kind": "image", "url": _image_url(report, node), "selector": selector}


def lazy_lcp(report):
    """True when the report's LCP image waits for a lazy-loader script: Lighthouse's
    LCP request discovery check fails, and the element carries a lazysizes class
    with a `data-src` or `data-srcset` the script swaps in."""
    items = _items(report, "lcp-discovery-insight")
    audit = (report.get("audits") or {}).get("lcp-discovery-insight") or {}
    checks = next((i.get("items") or {} for i in items if i.get("type") == "checklist"), {})
    failed = audit.get("score") == 0 or any(c.get("value") is False for c in checks.values())
    snippet = (_node(report) or {}).get("snippet") or ""
    return failed and bool(LAZY_CLASS.search(snippet)) and bool(LAZY_SOURCE.search(snippet))


def _image_url(report, node):
    """The LCP image's URL: the node's `src` (Lighthouse writes currentSrc there,
    cut to 75 characters), matched to the request that fetched it."""
    found = re.search(r'\ssrc="([^"]*)"', (node or {}).get("snippet") or "")
    if not found:
        return None
    src = html.unescape(found.group(1)).strip()
    cut = src.endswith("\u2026")
    src = src.rstrip("\u2026")
    if src.startswith("//"):
        src = "https:" + src
    if not src.startswith("https://") and not src.startswith("http://"):
        return None
    for item in requests(report):
        if item["url"].startswith(src):
            return item["url"]
    return None if cut else src


def place(url):
    """A URL without its query or fragment: the thing the probe protects."""
    parts = urlsplit(url)
    return "%s://%s%s" % (parts.scheme, parts.netloc, parts.path)


def build(reports, store_url, asset_path):
    """The probe for one page from its baseline reports.

    Returns {"patterns": [...], "protect": [...], "notes": [...]}: the patterns
    in a fixed order (scripts, fonts, images), the LCP image places no pattern
    may match, and a note for every request class the probe had to leave alone.
    """
    host = urlsplit(store_url).hostname
    origin = "https://%s" % host
    folder = origin + asset_path
    found = [lcp(r) for r in reports]
    protect = sorted({place(f["url"]) for f in found if f["kind"] == "image" and f["url"]})
    unknown_image = any(f["kind"] == "image" and not f["url"] for f in found)
    notes = []

    scripts, fonts, images = set(), set(), set()
    seen = {}
    for report in reports:
        for item in requests(report):
            url, kind = item["url"], item.get("resourceType")
            parts = urlsplit(url)
            where = place(url)
            seen.setdefault(where, set()).add(url)
            name = parts.path.rsplit("/", 1)[-1]
            extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            # A theme file's own folder and extension: assets/*.js, compiled_assets/*.js, assets/*.ttf
            in_folder = url.startswith(folder) and extension and "/" in url[len(folder):]
            by_type = in_folder and "%s%s/*.%s" % (folder, url[len(folder):].split("/", 1)[0], extension)
            if kind == "Script" and in_folder:
                scripts.add(by_type)
            elif kind == "Font":
                if in_folder:
                    fonts.add(by_type)
                elif parts.hostname == host and parts.path.startswith(FONT_LIBRARY):
                    fonts.add(origin + FONT_LIBRARY)
                elif parts.hostname == host:
                    fonts.add(where)
                elif parts.hostname == FONT_CDN:
                    fonts.add("https://%s/" % FONT_CDN)
            elif kind == "Image" and parts.hostname == host \
                    and parts.path.startswith(THEME_IMAGE_ROOT) and where not in protect:
                images.add(where)
    if unknown_image and images:
        notes.append("no theme image is blocked: the LCP image of a baseline Sample could not "
                     "be identified from its report, and the probe never risks blocking it")
        images = set()

    patterns = sorted(scripts) + sorted(fonts) + sorted(images)
    guarded = set(protect)
    for where in protect:
        guarded |= seen.get(where, set())
    kept = []
    for pattern in patterns:
        hit = next((url for url in sorted(guarded) if matches(pattern, url)), None)
        if hit:
            notes.append("dropped %s: it would also block the LCP image %s" % (pattern, hit))
        else:
            kept.append(pattern)
    return {"patterns": kept, "protect": protect, "notes": notes}


def check(report, probe):
    """Reject a Ceiling report in which a request for the protected LCP image failed."""
    protect = set(probe.get("protect") or [])
    for item in requests(report):
        if item.get("statusCode") == -1 and place(item["url"]) in protect:
            raise Rejected("lcp-blocked %s" % item["url"])
