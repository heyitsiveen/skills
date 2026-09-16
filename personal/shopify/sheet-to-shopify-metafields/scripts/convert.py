#!/usr/bin/env python3
"""
convert.py — Turn Source sheet cells into Converted values for Shopify metafields.

Used by the `sheet-to-shopify-metafields` skill. See SKILL.md for invocation context.

Everything between the Source sheet and the browser lives here, so the dangerous
step is deterministic and inspectable before any write:

  - Quote-aware TSV parsing (Sheets quotes cells holding tabs or newlines).
  - HTML -> the rich-text shape Shopify can actually store (ADR-0007):
    a definition list becomes ONE unordered list, one item per pair, each item
    the plain text "Term: value". A single <p> cell becomes one paragraph.
  - List metafields: several columns in, one ordered array of values out.
  - Backup files: written and read back here, so the format has one owner and
    "absent" survives the round trip.

Why a program and not prose: pasting a definition list into Shopify's rich-text
metafield editor discards <dl>, <dt>, <dd> AND the whitespace around them,
concatenating every term to its value with no separator -- Welding. It saves
without error and reads correctly in the admin's collapsed preview. A conversion
fault has to surface here, on screen, not on 76 live product pages.

Stdlib only. No install, nothing to clean up.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from html import escape, unescape
from html.parser import HTMLParser

# Tags the converter understands. Anything else stops the Run rather than being
# dropped -- silently dropping is exactly what Shopify's editor does, and it is
# the failure this whole module exists to prevent.
BLOCK_TAGS = {"dl", "dt", "dd", "p", "ul", "ol", "li"}
INLINE_TAGS = {"strong", "b", "em", "i", "a"}
KNOWN_TAGS = BLOCK_TAGS | INLINE_TAGS

RICH_TEXT = "rich_text_field"
LIST_TEXT = "list.single_line_text_field"
SINGLE_TEXT = "single_line_text_field"
MULTI_TEXT = "multi_line_text_field"
METAOBJECT = "metaobject_reference"

WRITABLE_TYPES = (RICH_TEXT, LIST_TEXT, SINGLE_TEXT, MULTI_TEXT)

DIGEST_SEP = "  ::  "

# A cell takes the block path only when it carries block-level markup. Most
# sheets carry none: their structure is newlines and bullet glyphs, and running
# those through an HTML parser damages ordinary prose -- "Size < 10cm" comes
# back as three paragraphs, and "<do not bleach>" stops the Run for nothing.
BLOCK_TAG_RE = re.compile(
    r"</?\s*(?:%s)\b" % "|".join(sorted(BLOCK_TAGS)), re.IGNORECASE
)

# Text shaped like a tag that names none the converter knows. Not markup, so it
# rides the line path as literal text -- but Pre-flight reports it, because a
# cell holding something tag-shaped is worth a human glance.
TAGLIKE_RE = re.compile(r"</?\s*[a-zA-Z][a-zA-Z0-9]*(?:\s[^<>]*)?/?>")

# On the line path only these inline runs are markup; everything else is
# literal. A targeted tokenizer rather than an HTML parser, so prose keeps its
# angle brackets.
INLINE_RUN_RE = re.compile(
    r"</?\s*(?:strong|b|em|i)\s*>|<\s*a\b[^<>]*>|</\s*a\s*>", re.IGNORECASE
)
HREF_RE = re.compile(r"""href\s*=\s*["']([^"']*)["']""", re.IGNORECASE)

# Bullet glyphs that start a list item. U+2022 is the one real sheets use; the
# rest are what people type when they have no bullet key.
BULLET_RE = re.compile(r"^\s*([•‣◦⁃∙*\-–—])\s+")

# Real HTML elements the converter cannot represent. Tag-shaped text naming one
# of these stops the Run -- it is markup, and Shopify would drop it silently.
# Tag-shaped text naming nothing on this list (`<do not bleach>`, `<size 10>`)
# is prose, and stays prose.
HTML_ELEMENTS = {
    "html", "head", "body", "table", "thead", "tbody", "tfoot", "tr", "td",
    "th", "caption", "colgroup", "col", "div", "span", "br", "hr", "img",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "code", "sup",
    "sub", "u", "s", "strike", "small", "big", "font", "center", "section",
    "article", "aside", "header", "footer", "nav", "main", "figure",
    "figcaption", "iframe", "script", "style", "link", "meta", "form",
    "input", "button", "select", "option", "textarea", "label", "video",
    "audio", "source", "picture", "svg", "path", "mark", "abbr", "cite",
    "q", "time", "wbr",
}


def _taglike_names(raw):
    """(matched text, element name) for every tag-shaped substring."""
    out = []
    for m in TAGLIKE_RE.finditer(raw or ""):
        name = re.match(r"</?\s*([a-zA-Z][a-zA-Z0-9]*)", m.group(0))
        out.append((m.group(0), name.group(1).lower() if name else ""))
    return out


def unsupported_elements(raw):
    """Real HTML elements present that the converter cannot represent."""
    return [n for _, n in _taglike_names(raw)
            if n in HTML_ELEMENTS and n not in KNOWN_TAGS]


class ConversionError(Exception):
    """A cell the converter refuses to guess at."""


# --------------------------------------------------------------------------
# TSV
# --------------------------------------------------------------------------


def parse_tsv(text):
    """Parse clipboard TSV into (headers, rows).

    Quote-aware: a cell holding a tab or a newline arrives quoted and must stay
    one cell.
    """
    reader = csv.reader(io.StringIO(text), delimiter="\t", quotechar='"')
    records = list(reader)
    if not records:
        return [], []
    headers = [h.strip() for h in records[0]]
    width = len(headers)
    rows = []
    for rec in records[1:]:
        if not any(c.strip() for c in rec):
            continue
        rec = (rec + [""] * width)[:width]
        rows.append(dict(zip(headers, rec)))
    return headers, rows


class _TableParser(HTMLParser):
    """Read the `text/html` flavour of a Sheets copy into cells.

    Worth preferring over the TSV flavour: a hyperlink in a sheet exists only
    as cell formatting, so `text/plain` returns the anchor text and drops the
    href. One real sheet carries 59 of them. Rich text has a link node, so
    they can be kept -- but only if the read sees them.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._row = None
        self._cell = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell = []
            self._depth = 0
        elif self._cell is not None:
            if tag == "br":
                self._cell.append("\n")
            elif tag == "a":
                href = dict(attrs).get("href") or ""
                self._cell.append('<a href="%s">' % escape(href, quote=True))
                self._depth += 1
            elif tag in ("p", "div") and self._cell:
                self._cell.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "tr":
            if self._row is not None and any(c.strip() for c in self._row):
                self.rows.append(self._row)
            self._row = None
        elif tag in ("td", "th"):
            if self._row is not None:
                self._row.append("".join(self._cell or []))
            self._cell = None
        elif tag == "a" and self._cell is not None and self._depth:
            self._cell.append("</a>")
            self._depth -= 1

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def parse_clipboard_html(html):
    """Parse the `text/html` clipboard flavour into (headers, rows).

    Cell values come back as text with `\\n` for line breaks and `<a href>`
    kept around linked runs -- the shape the line path expects.
    """
    p = _TableParser()
    p.feed(html)
    p.close()
    if not p.rows:
        return [], []
    headers = [h.strip() for h in p.rows[0]]
    width = len(headers)
    rows = []
    for rec in p.rows[1:]:
        rec = (rec + [""] * width)[:width]
        rows.append(dict(zip(headers, rec)))
    return headers, rows


def handle_from_url(url):
    """The last path segment of a product URL.

    Query and fragment come off before the trailing slash, or a URL ending
    `/?variant=1` leaves an empty last segment.
    """
    url = (url or "").strip()
    url = url.split("?")[0].split("#")[0].rstrip("/")
    return url.rsplit("/", 1)[-1] if url else ""


def row_url(row, mapping):
    """The product URL for a row, when the Mapping derives handles from one.

    A URL cell often carries link formatting, so the HTML read delivers it as
    `<a href="...">...</a>`. The href is the authoritative URL; without this
    the "last path segment" of the raw cell is `a>`, which looks like a handle
    and is not one.
    """
    spec = mapping.get("handle_column", "Handle")
    if not (isinstance(spec, dict) and "from_url" in spec):
        return ""
    cell = (row.get(spec["from_url"]) or "").strip()
    href = HREF_RE.search(cell)
    if href:
        return unescape(href.group(1)).strip()
    return unescape(re.sub(r"<[^>]+>", "", cell)).strip()


def row_handle(row, mapping, resolved=None):
    """The product handle for a row.

    Named directly by `handle_column`, or derived from a URL column when the
    sheet has no handle at all -- one real sheet identifies products only by
    `Product URL`.

    A derived handle is a guess until the URL has been visited. A renamed
    product keeps its old URL working and redirects to the new handle, so the
    derived value can be stale: it finds nothing, or finds the wrong product.
    `resolved` maps a sheet URL to what visiting it actually produced, and
    wins over derivation whenever it is present.
    """
    spec = mapping.get("handle_column", "Handle")
    if isinstance(spec, dict) and "from_url" in spec:
        url = row_url(row, mapping)
        if resolved and url in resolved:
            return (resolved[url].get("handle") or "").strip()
        return handle_from_url(url)
    return (row.get(spec) or "").strip()


def product_urls(rows, mapping):
    """The distinct product URLs a Run has to visit, in sheet order.

    Distinct, because a sheet can list one product twice and a page load is
    the expensive part of Pre-flight.
    """
    seen, out = set(), []
    for row in rows:
        url = row_url(row, mapping)
        if url and url not in seen:
            seen.add(url)
            out.append(url)
    return out


# --------------------------------------------------------------------------
# HTML -> blocks
# --------------------------------------------------------------------------


class _CellParser(HTMLParser):
    """Build a flat block list from one source cell.

    A block is {"kind": "list"|"paragraph", "items": [inlines]} where an inline
    is {"text": str, "bold": bool, "italic": bool, "href": str|None}.
    A paragraph block carries exactly one item.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.unknown = []
        self.malformed = []
        self._marks = []
        self._href = []
        self._buf = []
        self._pending_dt = None
        self._in = None

    def _flush_text(self):
        out, self._buf = self._buf, []
        return out

    def _current_list(self):
        if not self.blocks or self.blocks[-1]["kind"] != "list":
            self.blocks.append({"kind": "list", "items": []})
        return self.blocks[-1]

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag not in KNOWN_TAGS:
            self.unknown.append(tag)
            return
        if tag in INLINE_TAGS:
            if tag == "a":
                self._href.append(dict(attrs).get("href"))
            self._marks.append(tag)
            return
        if tag in ("dl", "ul", "ol"):
            self._current_list()
        elif tag in ("dt", "dd", "li", "p"):
            self._buf = []
            self._in = tag

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag not in KNOWN_TAGS:
            return
        if tag in INLINE_TAGS:
            if tag == "a" and self._href:
                self._href.pop()
            for i in range(len(self._marks) - 1, -1, -1):
                if self._marks[i] == tag:
                    self._marks.pop(i)
                    break
            return
        if tag == "dt":
            self._pending_dt = self._flush_text()
            self._in = None
        elif tag == "dd":
            value = self._flush_text()
            if self._pending_dt is None:
                self.malformed.append("<dd> with no preceding <dt>")
                self._in = None
                return
            term = self._pending_dt
            self._pending_dt = None
            self._current_list()["items"].append(_join_pair(term, value))
            self._in = None
        elif tag == "li":
            items = self._flush_text()
            if _inlines_text(items).strip():
                self._current_list()["items"].append(items)
            self._in = None
        elif tag == "p":
            items = self._flush_text()
            if _inlines_text(items).strip():
                self.blocks.append({"kind": "paragraph", "items": [items]})
            self._in = None
        elif tag in ("dl", "ul", "ol"):
            if self._pending_dt is not None:
                self.malformed.append("<dt> with no matching <dd>")
                self._pending_dt = None

    def handle_data(self, data):
        if self._in is None:
            if data.strip():
                self.blocks.append(
                    {"kind": "paragraph",
                     "items": [[_inline(data, self._marks, self._href)]]}
                )
            return
        if data:
            self._buf.append(_inline(data, self._marks, self._href))


def _inline(text, marks, hrefs):
    return {
        "text": text,
        "bold": any(m in ("strong", "b") for m in marks),
        "italic": any(m in ("em", "i") for m in marks),
        "href": hrefs[-1] if hrefs else None,
    }


def _inlines_text(inlines):
    return "".join(i["text"] for i in inlines)


def _join_pair(term, value):
    """A definition list item is the plain string "Term: value" (ADR-0007).

    The colon comes from the join, so a term that already ends in one does not
    get a second.
    """
    term = [dict(i) for i in term]
    if term:
        term[-1]["text"] = term[-1]["text"].rstrip().rstrip(":")
    joined = term + [{"text": ": ", "bold": False, "italic": False, "href": None}]
    value = [dict(i) for i in value]
    if value:
        value[0]["text"] = value[0]["text"].lstrip()
    return joined + value


def parse_cell(html):
    """Parse one source cell into blocks.

    Raises ConversionError on anything the converter will not guess at.
    """
    p = _CellParser()
    p.feed(html)
    p.close()
    if p.unknown:
        raise ConversionError(
            "unsupported tag(s): " + ", ".join(sorted(set(p.unknown)))
        )
    if p.malformed:
        raise ConversionError("; ".join(sorted(set(p.malformed))))
    return [b for b in p.blocks if b["items"]]


# --------------------------------------------------------------------------
# blocks -> Converted value
# --------------------------------------------------------------------------


def _inlines_html(inlines):
    out = []
    for i in inlines:
        s = escape(i["text"], quote=False)
        if i["bold"]:
            s = "<strong>%s</strong>" % s
        if i["italic"]:
            s = "<em>%s</em>" % s
        if i["href"]:
            s = '<a href="%s">%s</a>' % (escape(i["href"], quote=True), s)
        out.append(s)
    return "".join(out)


def render_html(blocks):
    """The fragment that goes on the clipboard as text/html.

    Shopify keeps exactly what maps onto its seven node types, so this emits
    only those.
    """
    out = []
    for b in blocks:
        if b["kind"] == "list":
            items = "".join("<li>%s</li>" % _inlines_html(i) for i in b["items"])
            out.append("<ul>%s</ul>" % items)
        else:
            out.append("<p>%s</p>" % _inlines_html(b["items"][0]))
    return "".join(out)


def render_plain(blocks):
    """The text/plain twin. Both flavours go on the clipboard together."""
    lines = []
    for b in blocks:
        for item in b["items"]:
            lines.append(_inlines_text(item).strip())
    return "\n".join(lines)


# --------------------------------------------------------------------------
# The line path -- for cells whose structure is newlines and bullet glyphs
# --------------------------------------------------------------------------

_TAG_OUT = {"b": "strong", "strong": "strong", "i": "em", "em": "em", "a": "a"}


def split_lines(raw):
    """Normalise line endings and drop the blank lines at either end.

    43 cells of one real sheet use CRLF and one column's cells end in three
    trailing newlines, which would otherwise become empty paragraphs.
    """
    text = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def render_line(s):
    """One line -> (html, plain).

    Only `<a>`, `<strong>`, `<b>`, `<em>` and `<i>` count as markup here.
    Everything else is literal, so prose keeps its angle brackets and a cell
    reading `100% cotton <do not bleach>` is text rather than a broken tag.
    """
    html, plain, pos = [], [], 0
    for m in INLINE_RUN_RE.finditer(s):
        chunk = unescape(s[pos:m.start()])
        html.append(escape(chunk, quote=False))
        plain.append(chunk)
        tok = m.group(0)
        low = tok.lower()
        if low.startswith("</"):
            html.append("</%s>" % _TAG_OUT[low[2:].strip(" >")])
        elif low.startswith("<a"):
            href = HREF_RE.search(tok)
            html.append('<a href="%s">' % escape(href.group(1), quote=True)
                        if href else "<a>")
        else:
            html.append("<%s>" % _TAG_OUT[low.strip("< >")])
        pos = m.end()
    chunk = unescape(s[pos:])
    html.append(escape(chunk, quote=False))
    plain.append(chunk)
    return "".join(html), "".join(plain).strip()


def lines_to_html_plain(lines):
    """Consecutive bullet lines become one list; every other line a paragraph.

    A blank line closes the list in progress, which is how these sheets
    separate one group of bullets from the next.
    """
    html_parts, plain_parts, buf = [], [], []

    def flush():
        if buf:
            html_parts.append(
                "<ul>%s</ul>" % "".join("<li>%s</li>" % h for h, _ in buf)
            )
            plain_parts.extend(p for _, p in buf)
            buf.clear()

    for line in lines:
        if not line.strip():
            flush()
            continue
        m = BULLET_RE.match(line)
        if m:
            buf.append(render_line(line[m.end():]))
            continue
        flush()
        h, p = render_line(line)
        if p:
            html_parts.append("<p>%s</p>" % h)
            plain_parts.append(p)
    flush()
    return "".join(html_parts), "\n".join(plain_parts)


def cell_kind(raw):
    """Which path a cell takes, and whether it holds anything tag-shaped."""
    raw = (raw or "").strip()
    if not raw:
        return "empty"
    if BLOCK_TAG_RE.search(raw):
        return "markup"
    return "text"


def taglike_unknown(raw):
    """Tag-shaped substrings naming no HTML element at all.

    Reported by Pre-flight rather than stopping the Run: these are prose that
    happens to use angle brackets, which is almost always what was meant. A
    substring naming a real element is a different thing and stops the Run.
    """
    return [text for text, name in _taglike_names(raw)
            if name not in KNOWN_TAGS and name not in HTML_ELEMENTS]


# --------------------------------------------------------------------------
# blocks or lines -> Converted value
# --------------------------------------------------------------------------


def convert_cell(raw, target_type):
    """One source cell -> one Converted value, or None for an empty cell."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if target_type == LIST_TEXT:
        return convert_list([raw])
    if target_type in (SINGLE_TEXT, MULTI_TEXT):
        # Plain-text destinations. No markup is produced, and the text is not
        # reshaped -- a single-line field is refused rather than silently
        # flattened, because joining lines is a guess about what was meant.
        lines = split_lines(raw)
        plains = [p for p in (render_line(ln)[1] for ln in lines) if p]
        if not plains:
            return None
        if target_type == SINGLE_TEXT and len(plains) > 1:
            raise ConversionError(
                "a single line text field cannot hold %d lines" % len(plains))
        return {"text": "\n".join(plains),
                "kind": "text" if len(plains) == 1 else "multiline"}
    if cell_kind(raw) == "markup":
        blocks = parse_cell(raw)
        if not blocks:
            return None
        return {"html": render_html(blocks), "plain": render_plain(blocks),
                "kind": "markup"}
    bad = unsupported_elements(raw)
    if bad:
        raise ConversionError("unsupported tag(s): " + ", ".join(sorted(set(bad))))
    html, plain = lines_to_html_plain(split_lines(raw))
    if not html:
        return None
    return {"html": html, "plain": plain, "kind": "text"}


def convert_list(cells):
    """Columns and lines -> one ordered array of plain values.

    A mapped column contributes its cell; a cell holding several lines
    contributes one value per line, bullet glyphs stripped. Both compose, so
    three bullet columns and one bulleted cell reach the same place.
    """
    values = []
    for cell in cells:
        for line in split_lines(cell):
            if not line.strip():
                continue
            m = BULLET_RE.match(line)
            _, plain = render_line(line[m.end():] if m else line)
            if plain:
                values.append(plain)
    return {"values": values} if values else None


# --------------------------------------------------------------------------
# Run-level conversion
# --------------------------------------------------------------------------


def group_identical(converted):
    """Identical values written once per group, not once per product.

    On the first target catalogue 76 products shared 14 distinct brew blocks.
    """
    groups = {}
    for c in converted:
        body = c.get("html") or json.dumps(c.get("values"), sort_keys=True)
        digest = hashlib.sha256(
            (c["key"] + DIGEST_SEP + body).encode("utf-8")
        ).hexdigest()[:12]
        groups.setdefault(digest, {"key": c["key"], "handles": []})
        groups[digest]["handles"].append(c["handle"])
    return {d: g for d, g in groups.items() if len(g["handles"]) > 1}


def _check_against_structure(target, key, meta, fields):
    """One target, checked against what the store actually has."""
    out = []
    path = target.get("path")

    if not path:
        have = fields.get(key)
        if have is None:
            out.append("%s does not exist on the store" % key)
        elif have != target.get("type"):
            out.append("%s is %r on the store, not %r"
                       % (key, have, target.get("type")))
        return out

    if key not in fields:
        out.append("%s does not exist on the store" % key)

    for step in path:
        definition = step.get("definition")
        defn = meta.get(definition)
        if defn is None:
            out.append("%s: metaobject %r does not exist on the store"
                       % (key, definition))
            continue
        field = step.get("field")
        if field not in defn.get("fields", {}):
            out.append("%s: metaobject %r has no field %r (it has: %s)"
                       % (key, definition, field,
                          ", ".join(sorted(defn.get("fields", {})))))
        elif step.get("type") and defn["fields"][field] != step["type"]:
            out.append("%s: %s.%s is %r on the store, not %r"
                       % (key, definition, field,
                          defn["fields"][field], step["type"]))

    split = target.get("split")
    if split and path:
        definition = path[-1].get("definition")
        defn = meta.get(definition) or {}
        for part in split.get("parts") or []:
            name = part.get("field")
            have = defn.get("fields", {}).get(name)
            if have is None:
                out.append("%s: split writes %r, which metaobject %r does not "
                           "have" % (key, name, definition))
            elif part.get("type") and have != part["type"]:
                out.append("%s: %s.%s is %r on the store, not %r"
                           % (key, definition, name, have, part["type"]))
    return out


ATTRIBUTION_RE = re.compile(r"^(.*?)(\s*[—–]\s*\S.*)$", re.DOTALL)


def split_attribution(text):
    """Split a quotation from its trailing attribution.

    One sheet column holds both — `"…the workmanship." — Chris` — while the
    store keeps them in two fields, `quote` and `author`. Writing the whole
    cell into `quote` duplicates the name and leaves `author` stale.

    The split is at the LAST dash, because a dash inside the quotation is
    ordinary. The attribution keeps its leading whitespace and its dash
    exactly as the sheet wrote them.

    Returns (quote, attribution); attribution is "" when there is no dash.
    """
    text = (text or "").rstrip()
    best = None
    for m in re.finditer(r"[—–]", text):
        best = m.start()
    if best is None:
        return text, ""
    lead = len(text[:best].rstrip())
    return text[:best].rstrip(), text[lead:]


SPLIT_RULES = {"trailing-attribution": split_attribution}


def target_field_type(target):
    """The field type a target's Converted value has to suit.

    For a plain metafield that is the target's own type. For a metaobject the
    text does not live in the product metafield at all -- that only points at
    an entry -- so it is the type of the leaf field at the end of the path.
    """
    path = target.get("path")
    if path:
        return path[-1].get("type", RICH_TEXT)
    return target["type"]


def check_mapping(mapping, structure=None):
    """Refuse a Mapping that cannot be written, before anything reads a sheet.

    With `structure` — what Pre-flight actually found on the store — this also
    checks every destination exists and every type agrees. Knowing the
    destination's shape before converting is what lets one sheet column reach
    two fields: a `quote`/`author` pair cannot be discovered from the sheet.
    """
    problems = []
    meta = (structure or {}).get("metaobjects", {})
    fields = (structure or {}).get("product_metafields", {})

    for t in mapping.get("targets", []):
        key = t.get("key", "<no key>")
        if not t.get("columns"):
            problems.append("%s names no columns" % key)

        split = t.get("split")
        if split:
            rule = split.get("rule")
            if rule not in SPLIT_RULES:
                problems.append("%s uses unknown split rule %r; known: %s"
                                % (key, rule, ", ".join(sorted(SPLIT_RULES))))
            parts = split.get("parts") or []
            if len(parts) != 2:
                problems.append("%s split needs exactly two parts, got %d"
                                % (key, len(parts)))
            for p in parts:
                if not p.get("field") or not p.get("type"):
                    problems.append(
                        "%s split part needs both `field` and `type`" % key)

        if structure is not None:
            problems.extend(_check_against_structure(t, key, meta, fields))

        if t.get("type") == METAOBJECT or t.get("path"):
            path = t.get("path")
            if not path:
                problems.append(
                    "%s is a metaobject reference but has no path to the field "
                    "holding the text" % key)
                continue
            for i, step in enumerate(path):
                if not step.get("definition") or not step.get("field"):
                    problems.append(
                        "%s path step %d needs both `definition` and `field`"
                        % (key, i + 1))
            if not path[-1].get("type"):
                problems.append(
                    "%s path ends without a `type` on the leaf field" % key)
        elif t.get("type") not in WRITABLE_TYPES:
            problems.append(
                "%s has type %r, which this skill cannot write. Writable: %s"
                % (key, t.get("type"), ", ".join(WRITABLE_TYPES)))
    return problems


def metaobject_cost(converted):
    """How many entry saves a Run of these Converted values implies.

    The admin offers no bulk editing for metaobject entries -- the entries
    list's whole bulk menu is a Delete button -- so every entry is opened and
    saved one at a time. Pre-flight states this before the user commits.
    """
    entries = set()
    for c in converted:
        path = c.get("path")
        if not path:
            continue
        # Entries, not records: a split writes two fields of ONE entry, which
        # is one save, not two.
        entries.add((c["handle"], path[-1]["definition"]))
    per_definition = {}
    for _, definition in entries:
        per_definition[definition] = per_definition.get(definition, 0) + 1
    return {
        "entry_saves": len(entries),
        "by_definition": dict(sorted(per_definition.items())),
    }


def _records_for(target, n, handle, key, ttype, value, row, failures):
    """The Converted value(s) one target produces for one row.

    Usually one. A target carrying a `split` produces two, because the sheet
    keeps in one column what the store keeps in two fields.
    """
    path = target.get("path")
    split = target.get("split")

    if not split:
        record = dict(row=n, handle=handle, key=key, type=ttype, **value)
        if path:
            # Where the value actually goes: the product metafield only points
            # at an entry, and the text may be another hop beyond it.
            record["path"] = path
        return [record]

    source = row.get(target["columns"][0], "")
    head, tail = SPLIT_RULES[split["rule"]](source)
    out = []
    for part, text in zip(split["parts"], (head, tail)):
        if not text.strip():
            continue
        try:
            piece = convert_cell(text, part["type"])
        except ConversionError as e:
            failures.append({"row": n, "handle": handle, "key": key,
                             "field": part["field"], "reason": str(e)})
            continue
        if piece is None:
            continue
        record = dict(row=n, handle=handle, key=key, type=part["type"],
                      field=part["field"], **piece)
        if path:
            record["path"] = path[:-1] + [dict(path[-1], field=part["field"],
                                               type=part["type"])]
        out.append(record)
    return out


def convert_rows(rows, mapping, resolved=None):
    """Every mapped cell of every row. Returns (converted, report)."""
    converted, skipped, failures = [], [], []
    seen = {}
    unresolved, renamed, titles = [], [], {}
    derives = isinstance(mapping.get("handle_column", "Handle"), dict)

    for n, row in enumerate(rows, start=2):  # sheet row numbers; header is row 1
        handle = row_handle(row, mapping, resolved)
        if derives:
            url = row_url(row, mapping)
            if not url:
                unresolved.append({"row": n, "reason": "no product URL in the row"})
            elif resolved is None or url not in resolved:
                unresolved.append({"row": n, "url": url,
                                   "derived": handle_from_url(url),
                                   "reason": "URL not visited yet"})
            else:
                entry = resolved[url]
                guess = handle_from_url(url)
                if entry.get("title"):
                    titles[handle] = entry["title"]
                if handle and guess and handle != guess:
                    renamed.append({"row": n, "url": url, "derived": guess,
                                    "actual": handle,
                                    "title": entry.get("title", "")})
        seen.setdefault(handle, []).append(n)
        for target in mapping["targets"]:
            key, cols = target["key"], target["columns"]
            ttype = target_field_type(target)
            try:
                if ttype == LIST_TEXT:
                    value = convert_list([row.get(c, "") for c in cols])
                else:
                    value = convert_cell(row.get(cols[0], ""), ttype)
            except ConversionError as e:
                failures.append(
                    {"row": n, "handle": handle, "key": key, "reason": str(e)}
                )
                continue
            if value is None:
                skipped.append({"row": n, "handle": handle, "key": key,
                                "reason": "empty source cell"})
                continue
            for record in _records_for(target, n, handle, key, ttype, value,
                                       row, failures):
                converted.append(record)

    duplicates = {h: rs for h, rs in seen.items() if h and len(rs) > 1}
    report = {
        "rows": len(rows),
        "converted": len(converted),
        "skipped": skipped,
        "failures": failures,
        "duplicate_handles": duplicates,
        "groups": group_identical(converted),
    }
    if derives:
        # A derived handle is a guess. These three say how good a guess it was.
        report["unresolved_urls"] = unresolved
        report["renamed_products"] = renamed
        report["titles"] = titles
    cost = metaobject_cost(converted)
    if cost["entry_saves"]:
        report["metaobjects"] = cost
    return converted, report


def tag_inventory(rows, mapping):
    """Every distinct tag present in the mapped columns.

    Pre-flight reports it so a tag the converter cannot handle is found before
    the write, not after. Only cells on the markup path can fail on one --
    a tag-shaped string in a text cell is literal, and is reported separately.
    """
    tags = {}
    cols = [c for t in mapping["targets"] for c in t["columns"]]
    for row in rows:
        for col in cols:
            cell = row.get(col, "") or ""
            if cell_kind(cell) != "markup":
                continue
            for m in re.finditer(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9]*)", cell):
                name = m.group(1).lower()
                tags[name] = tags.get(name, 0) + 1
    return {
        "counts": tags,
        "unsupported": sorted(t for t in tags if t not in KNOWN_TAGS),
    }


def column_shapes(rows, mapping):
    """What each mapped column actually holds, so Pre-flight can say so.

    Most sheets carry no markup at all -- their structure is newlines and
    bullet glyphs. Saying which path a column takes is the difference between
    a Run the user can sanity-check and one they have to trust.
    """
    cols = [c for t in mapping["targets"] for c in t["columns"]]
    out = {}
    for col in cols:
        counts = {"markup": 0, "text": 0, "empty": 0}
        bullets = links = multiline = 0
        taglike = []
        for row in rows:
            cell = row.get(col, "") or ""
            counts[cell_kind(cell)] += 1
            lines = split_lines(cell)
            if len(lines) > 1:
                multiline += 1
            if any(BULLET_RE.match(ln) for ln in lines):
                bullets += 1
            if "<a " in cell.lower():
                links += 1
            taglike.extend(taglike_unknown(cell) if cell_kind(cell) == "text" else [])
        out[col] = {
            "markup": counts["markup"], "text": counts["text"],
            "empty": counts["empty"], "multiline": multiline,
            "bulleted": bullets, "with_links": links,
            "taglike_text": sorted(set(taglike))[:10],
        }
    return out


# --------------------------------------------------------------------------
# Comparing what is there against what the Run intends
# --------------------------------------------------------------------------

WS_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")


def _normalised(value):
    """Collapse the differences that are not differences."""
    if isinstance(value, list):
        return [WS_RE.sub(" ", str(v)).strip() for v in value]
    return WS_RE.sub(" ", str(value or "")).strip()


def _styling(html):
    """The editorial styling a value carries, which plain sheet text cannot."""
    text = str(html or "")
    return {
        "bold": bool(re.search(r"<(strong|b)\b", text, re.I)),
        "italic": bool(re.search(r"<(em|i)\b", text, re.I)),
        "links": len(re.findall(r"<a\b", text, re.I)),
    }


def compare_value(current, intended):
    """One field: is it already right, and what would writing it destroy?

    The `sheet is authoritative` policy means the Run overwrites whatever
    editorial styling the store carries. That is a decision, not an accident,
    so it is reported before the write rather than discovered after it.
    """
    if _normalised(current) == _normalised(intended):
        return {"status": "already correct", "removes": []}

    have, want = _styling(current), _styling(intended)
    removes = []
    if have["bold"] and not want["bold"]:
        removes.append("bold")
    if have["italic"] and not want["italic"]:
        removes.append("italic")
    if have["links"] > want["links"]:
        removes.append("%d link(s)" % (have["links"] - want["links"]))
    return {"status": "differs", "removes": removes}


def _body_of(record):
    """Whatever a Converted value actually carries, for comparison."""
    for key in ("html", "text", "values"):
        if key in record:
            return record[key]
    return ""


def diff_run(converted, current):
    """Every intended value against what the store holds now.

    Doubles as the verify-first pass: run it, change nothing, read the table.
    """
    have = {}
    for c in current:
        have[(c.get("handle"), c.get("key"), c.get("field"))] = c.get("value")

    rows, counts = [], {"already correct": 0, "differs": 0, "not read": 0}
    removes_total = {}
    for record in converted:
        ident = (record["handle"], record["key"], record.get("field"))
        if ident not in have:
            rows.append({"handle": record["handle"], "key": record["key"],
                         "field": record.get("field"),
                         "status": "not read",
                         "reason": "no current value captured"})
            counts["not read"] += 1
            continue
        verdict = compare_value(have[ident], _body_of(record))
        counts[verdict["status"]] += 1
        for r in verdict["removes"]:
            label = re.sub(r"^\d+ ", "", r)
            removes_total[label] = removes_total.get(label, 0) + 1
        rows.append({"handle": record["handle"], "key": record["key"],
                     "field": record.get("field"), **verdict})
    return {
        "summary": counts,
        "would_remove": dict(sorted(removes_total.items())),
        "fields": rows,
    }


# --------------------------------------------------------------------------
# Matching the sheet against the admin
# --------------------------------------------------------------------------


def match_admin(converted, admin_handles, page_size=50):
    """Plan the write against the admin's own order, not the sheet's.

    The bulk editor is positional: content goes to a row by where it sits on
    screen. The sheet's order and the admin's order have no reason to agree,
    so nothing may be written by position from the sheet. The handle is the
    only thing tying a row to a product, and this is where that is enforced.

    The grid drives. For each page of the admin list, this says which visible
    rows to write and what goes in them; every other row is left alone.
    """
    by_handle = {}
    for c in converted:
        by_handle.setdefault(c["handle"], []).append(c)

    admin_order = {h: i for i, h in enumerate(admin_handles)}
    sheet_handles = [h for h in by_handle if h]

    missing = sorted(h for h in sheet_handles if h not in admin_order)
    matched = sorted(h for h in sheet_handles if h in admin_order)

    pages = {}
    for handle in matched:
        index = admin_order[handle]
        page = index // page_size + 1
        pages.setdefault(page, []).append({
            # Where the product sits in the PRODUCT LIST, for a human to check
            # against. It is not a row number in the bulk editor: a product
            # with variants expands into extra rows there, so the grid holds
            # more rows than products and counting them lands on the wrong one.
            "list_position": index % page_size + 1,
            "handle": handle,
            "fields": sorted(c["key"] for c in by_handle[handle]),
        })
    batches = [{"page": p, "write": sorted(rows, key=lambda r: r["list_position"])}
               for p, rows in sorted(pages.items())]

    # Do the two orders agree? Only informative -- the plan above holds either
    # way -- but it is the thing a human wants to see stated.
    seen = set()
    sheet_seq = []
    for c in converted:
        h = c["handle"]
        if h in admin_order and h not in seen:
            seen.add(h)
            sheet_seq.append(h)
    matched_set = set(matched)
    admin_seq = [h for h in admin_handles if h in matched_set]

    return {
        "sheet_handles": len(sheet_handles),
        "admin_products": len(admin_handles),
        "matched": len(matched),
        "missing_from_admin": missing,
        "untouched_admin_products": len(admin_handles) - len(matched),
        "orders_agree": sheet_seq == admin_seq,
        "pages_to_visit": [b["page"] for b in batches],
        "batches": batches,
    }


# --------------------------------------------------------------------------
# Backup
# --------------------------------------------------------------------------


def backup_write(path, store, entries):
    """Write a Backup file.

    Entries are {handle, key, type, value} where value is None for a field that
    holds nothing. None survives the round trip, so an Undo can restore absent
    as absent rather than writing an empty string.
    """
    doc = {"store": store, "version": 1, "entries": entries}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return doc


def backup_read(path):
    """Read a Backup into the two sets an Undo needs: restore, and delete."""
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    if doc.get("version") != 1:
        raise ConversionError("unrecognised Backup version: %r" % doc.get("version"))
    entries = doc["entries"]
    return {
        "store": doc.get("store"),
        "entries": entries,
        "restore": [e for e in entries if e.get("value") is not None],
        "delete": [e for e in entries if e.get("value") is None],
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _emit(obj):
    json.dump(obj, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Turn Source sheet cells into Converted values."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    def source_args(parser):
        # --html is preferred: it is the only read that keeps a sheet's
        # hyperlinks, which exist as cell formatting and vanish from the TSV.
        parser.add_argument("--html", help="the text/html clipboard flavour")
        parser.add_argument("--tsv", help="the text/plain clipboard flavour")

    p = sub.add_parser("rows", help="parse a clipboard payload into rows")
    source_args(p)

    p = sub.add_parser("urls", help="the product URLs Pre-flight has to visit")
    source_args(p)
    p.add_argument("--mapping", required=True)

    p = sub.add_parser("inspect", help="Pre-flight: headers, count, shapes, tags")
    source_args(p)
    p.add_argument("--mapping", required=True)
    p.add_argument("--resolved", help="JSON from visiting each product URL")
    p.add_argument("--structure", help="what Pre-flight found on the store")

    p = sub.add_parser("convert", help="every mapped cell into Converted values")
    source_args(p)
    p.add_argument("--mapping", required=True)
    p.add_argument("--resolved", help="JSON from visiting each product URL")
    p.add_argument("--structure", help="what Pre-flight found on the store")
    p.add_argument("--out")

    p = sub.add_parser("diff", help="what is there vs what the Run intends")
    p.add_argument("--converted", required=True)
    p.add_argument("--current", required=True,
                   help="JSON list of {handle, key, field, value} read from the store")

    p = sub.add_parser("match", help="plan the write against the admin's order")
    p.add_argument("--converted", required=True)
    p.add_argument("--admin", required=True,
                   help="JSON list of admin product handles, in list order")
    p.add_argument("--page-size", type=int, default=50)

    p = sub.add_parser("backup-write", help="write a Backup file")
    p.add_argument("--store", required=True)
    p.add_argument("--entries", required=True, help="JSON file of captured entries")
    p.add_argument("--out", required=True)

    p = sub.add_parser("backup-read", help="read a Backup into restore/delete sets")
    p.add_argument("--file", required=True)

    args = ap.parse_args(argv)

    def load():
        if getattr(args, "html", None):
            return parse_clipboard_html(_read(args.html))
        if getattr(args, "tsv", None):
            return parse_tsv(_read(args.tsv))
        ap.error("give --html (preferred, keeps hyperlinks) or --tsv")

    def resolved():
        path = getattr(args, "resolved", None)
        return json.loads(_read(path)) if path else None

    if args.cmd == "rows":
        headers, rows = load()
        _emit({"headers": headers, "count": len(rows), "rows": rows})
        return 0

    if args.cmd == "urls":
        headers, rows = load()
        mapping = json.loads(_read(args.mapping))
        urls = product_urls(rows, mapping)
        _emit({"count": len(urls), "urls": urls,
               "note": "visit each, record the final URL after redirects and "
                       "the product title, as {url: {handle, title}}"})
        return 0

    if args.cmd == "inspect":
        headers, rows = load()
        mapping = json.loads(_read(args.mapping))
        struct = getattr(args, "structure", None)
        bad_mapping = check_mapping(
            mapping, json.loads(_read(struct)) if struct else None)
        if bad_mapping:
            _emit({"error": "the Mapping cannot be written as written",
                   "problems": bad_mapping})
            return 1
        tags = tag_inventory(rows, mapping)
        _, report = convert_rows(rows, mapping, resolved())
        missing = [c for t in mapping["targets"] for c in t["columns"]
                   if c not in headers]
        spec = mapping.get("handle_column", "Handle")
        handle_source = ("derived from " + spec["from_url"]
                         if isinstance(spec, dict) else spec)
        _emit({
            "headers": headers,
            "count": len(rows),
            "read_as": "html" if getattr(args, "html", None) else "tsv",
            "handle_from": handle_source,
            "columns_not_in_sheet": missing,
            "column_shapes": column_shapes(rows, mapping),
            "tags": tags,
            "skipped": report["skipped"],
            "failures": report["failures"],
            "duplicate_handles": report["duplicate_handles"],
            "metaobjects": report.get("metaobjects"),
            "unresolved_urls": report.get("unresolved_urls", []),
            "renamed_products": report.get("renamed_products", []),
            "groups": report["groups"],
        })
        return 1 if (missing or tags["unsupported"] or report["failures"]) else 0

    if args.cmd == "convert":
        headers, rows = load()
        mapping = json.loads(_read(args.mapping))
        struct = getattr(args, "structure", None)
        bad_mapping = check_mapping(
            mapping, json.loads(_read(struct)) if struct else None)
        if bad_mapping:
            _emit({"error": "the Mapping cannot be written as written",
                   "problems": bad_mapping})
            return 1
        res = resolved()
        converted, report = convert_rows(rows, mapping, res)
        if report.get("unresolved_urls"):
            _emit({"error": "handles are derived from URLs that have not been "
                            "visited; run `urls`, visit each, and pass "
                            "--resolved",
                   "unresolved_urls": report["unresolved_urls"]})
            return 1
        if report["failures"]:
            out = {"error": "conversion failed; nothing written"}
            out.update(report)
            _emit(out)
            return 1
        payload = {"converted": converted, "report": report}
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
                f.write("\n")
            _emit({"written": args.out, "report": report})
        else:
            _emit(payload)
        return 0

    if args.cmd == "diff":
        payload = json.loads(_read(args.converted))
        converted = payload.get("converted", payload)
        result = diff_run(converted, json.loads(_read(args.current)))
        _emit(result)
        return 0

    if args.cmd == "match":
        payload = json.loads(_read(args.converted))
        converted = payload.get("converted", payload)
        admin = json.loads(_read(args.admin))
        if isinstance(admin, dict):
            admin = admin.get("handles", [])
        result = match_admin(converted, admin, args.page_size)
        _emit(result)
        return 1 if result["missing_from_admin"] else 0

    if args.cmd == "backup-write":
        entries = json.loads(_read(args.entries))
        backup_write(args.out, args.store, entries)
        _emit({"written": args.out, "entries": len(entries),
               "absent": sum(1 for e in entries if e.get("value") is None)})
        return 0

    if args.cmd == "backup-read":
        _emit(backup_read(args.file))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
