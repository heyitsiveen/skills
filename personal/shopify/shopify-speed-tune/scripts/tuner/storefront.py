"""Reading the public storefront with curl.

Python's own HTTP client is challenged by Cloudflare on some stores while curl
with a browser user agent is not, so every storefront read goes through curl.
"""

import json
import os
import re
import tempfile
import time
from urllib.parse import urljoin, urlsplit

from tuner.output import Failed, Refused
from tuner.proc import run

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36")


class Response:
    def __init__(self, url, status, headers, body):
        self.url = url
        self.status = status
        self.headers = headers  # lower-case name -> list of values
        self.body = body

    def header(self, name):
        values = self.headers.get(name.lower(), [])
        return values[-1] if values else None

    def served_theme(self):
        """The theme id that rendered this response, from its server-timing header."""
        for value in self.headers.get("server-timing", []):
            m = re.search(r'theme;desc="?(\d+)"?', value)
            if m:
                return int(m.group(1))
        return None


def base_url(text):
    """The store URL as `https://<host>/`, or a refusal when it has no host."""
    value = text.strip()
    if "://" not in value:
        value = "https://" + value
    host = urlsplit(value).hostname
    if not host or "." not in host:
        raise Refused("bad-store-url", "%r is not a store URL" % text)
    return "https://%s/" % host.lower()


def _parse_headers(raw):
    blocks = [b for b in re.split(r"\r?\n\r?\n", raw) if b.strip()]
    status, headers = 0, {}
    for block in blocks:  # curl writes one block per response; keep the last
        lines = block.splitlines()
        m = re.match(r"HTTP/[\d.]+\s+(\d+)", lines[0]) if lines else None
        if not m:
            continue
        status, headers = int(m.group(1)), {}
        for line in lines[1:]:
            name, sep, value = line.partition(":")
            if sep:
                headers.setdefault(name.strip().lower(), []).append(value.strip())
    return status, headers


def fetch(url, cookie=None, timeout=30):
    """GET one URL without following redirects. `cookie` never reaches argv."""
    with tempfile.TemporaryDirectory(prefix="speed-tune-fetch-") as tmp:
        head, body = os.path.join(tmp, "head"), os.path.join(tmp, "body")
        argv = ["curl", "-sS", "--max-time", str(timeout), "-A", USER_AGENT, "-D", head, "-o", body]
        if cookie:
            sent = os.path.join(tmp, "sent")
            with open(os.open(sent, os.O_WRONLY | os.O_CREAT, 0o600), "w", encoding="utf-8") as f:
                f.write("Cookie: %s\n" % cookie)
            argv += ["-H", "@" + sent]
        argv.append(url)
        proc = run(argv, timeout=timeout + 15)
        if proc.returncode != 0:
            raise Failed("store-unreachable", "curl %s exited %d: %s"
                         % (url, proc.returncode, proc.stderr.strip()[:200]))
        with open(head, encoding="utf-8", errors="replace") as f:
            status, headers = _parse_headers(f.read())
        text = ""
        if os.path.exists(body):
            with open(body, encoding="utf-8", errors="replace") as f:
                text = f.read()
    response = Response(url, status, headers, text)
    if response.header("cf-mitigated") or (status == 403 and "Verifying your connection" in text):
        raise Failed("store-blocked", "%s answered with a bot challenge, not a page" % url)
    return response


def preview_url(url):
    """The URL an unpublished theme's page is loaded from: the page URL plus `pb=0`.

    With the preview cookie, the plain URL renders the theme but also injects
    Shopify's preview bar; `pb=0` leaves the bar out, and unlike
    `preview_theme_id` it adds no redirect.
    """
    return url + ("&" if "?" in url else "?") + "pb=0"


SHARING = "/services/access_tokens/create_sharing/"


def preview_cookie(store_url, theme_id):
    """The cookie that makes the plain storefront URL render an unpublished theme.

    Shopify answers `/?preview_theme_id=<id>` with a redirect that sets
    `_shopify_essential`. Sent alone on a plain URL, that cookie first redirects
    to a `create_sharing` URL; once the cookie has visited that URL, the plain
    URL renders the theme. The query parameter itself is never used for a
    Sample: its redirect adds most of a second to every load.
    Returns `_shopify_essential=<value>`, already shared.
    """
    for attempt in (1, 2):
        response = fetch("%s?preview_theme_id=%s" % (store_url, theme_id))
        cookie = None
        for value in response.headers.get("set-cookie", []):
            m = re.match(r"\s*(_shopify_essential=[^;]+)", value)
            if m:
                cookie = m.group(1)
        if cookie is None:
            raise Failed("preview-refused", "%s set no preview cookie for theme %s (HTTP %d)"
                         % (store_url, theme_id, response.status))
        plain = fetch(store_url, cookie=cookie)
        target = plain.header("location") or ""
        if SHARING not in target:
            return cookie
        fetch(urljoin(store_url, target), cookie=cookie)
        if SHARING not in (fetch(store_url, cookie=cookie).header("location") or ""):
            return cookie
        if attempt == 1:
            time.sleep(float(os.environ.get("SPEED_TUNE_POLL_SECONDS", "10")))
    raise Failed("preview-refused", "%s refused to share a preview of theme %s"
                 % (store_url, theme_id))


def verify_theme(url, cookie, theme_id):
    """Fetch `url` with the preview cookie and return the theme's asset folder.

    A missing or ignored cookie fails silently, because the store then serves
    its published theme; so the served theme is read back every time.
    """
    response = fetch(url, cookie=cookie)
    if response.status != 200:
        raise Failed("preview-failed", "%s answered HTTP %d with theme %s's preview cookie"
                     % (url, response.status, theme_id))
    served = response.served_theme()
    if served != theme_id:
        raise Failed("preview-ignored", "%s served theme %s, not %s, with its preview cookie"
                     % (url, served, theme_id))
    assets = asset_path_in(response.body)
    if not assets:
        raise Failed("preview-failed", "%s links no /cdn/shop/t/<n>/assets/ file" % url)
    return assets


def asset_path_in(html):
    """The theme's asset folder, `/cdn/shop/t/<n>/`, as the page's HTML links it.

    The number is a per-theme counter, not the theme id, so it is learned here.
    """
    found = re.findall(r"/cdn/shop/t/(\d+)/assets/", html)
    if not found:
        return None
    most = max(set(found), key=found.count)
    return "/cdn/shop/t/%s/" % most


def shop(store_url):
    """The shop behind a public storefront: its myshopify domain and primary URL."""
    response = fetch(store_url + "meta.json")
    try:
        meta = json.loads(response.body) if response.status == 200 else None
    except ValueError:
        meta = None
    if not meta or not meta.get("myshopify_domain"):
        raise Failed("store-unreadable", "%smeta.json did not describe a Shopify store (HTTP %d)"
                     % (store_url, response.status))
    return meta
