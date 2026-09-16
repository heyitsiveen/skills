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

DIGEST_SEP = "  ::  "


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


def convert_cell(raw, target_type):
    """One source cell -> one Converted value, or None for an empty cell."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if target_type == LIST_TEXT:
        return {"values": [unescape(raw)]}
    blocks = parse_cell(raw)
    if not blocks:
        return None
    return {"html": render_html(blocks), "plain": render_plain(blocks)}


def convert_list(cells):
    """Several columns -> one ordered array. Empty cells drop out; order holds."""
    values = [unescape(c.strip()) for c in cells if c and c.strip()]
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


def convert_rows(rows, mapping):
    """Every mapped cell of every row. Returns (converted, report)."""
    handle_col = mapping.get("handle_column", "Handle")
    converted, skipped, failures = [], [], []
    seen = {}

    for n, row in enumerate(rows, start=2):  # sheet row numbers; header is row 1
        handle = (row.get(handle_col) or "").strip()
        seen.setdefault(handle, []).append(n)
        for target in mapping["targets"]:
            key, ttype, cols = target["key"], target["type"], target["columns"]
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
            converted.append(dict(row=n, handle=handle, key=key, type=ttype, **value))

    duplicates = {h: rs for h, rs in seen.items() if h and len(rs) > 1}
    report = {
        "rows": len(rows),
        "converted": len(converted),
        "skipped": skipped,
        "failures": failures,
        "duplicate_handles": duplicates,
        "groups": group_identical(converted),
    }
    return converted, report


def tag_inventory(rows, mapping):
    """Every distinct tag present in the mapped columns.

    Pre-flight reports it so a tag the converter cannot handle is found before
    the write, not after.
    """
    tags = {}
    cols = [c for t in mapping["targets"] for c in t["columns"]]
    for row in rows:
        for col in cols:
            cell = row.get(col, "") or ""
            for m in re.finditer(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9]*)", cell):
                name = m.group(1).lower()
                tags[name] = tags.get(name, 0) + 1
    return {
        "counts": tags,
        "unsupported": sorted(t for t in tags if t not in KNOWN_TAGS),
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

    p = sub.add_parser("rows", help="parse a clipboard TSV into rows")
    p.add_argument("--tsv", required=True)

    p = sub.add_parser("inspect", help="Pre-flight: headers, count, tags, blanks")
    p.add_argument("--tsv", required=True)
    p.add_argument("--mapping", required=True)

    p = sub.add_parser("convert", help="every mapped cell into Converted values")
    p.add_argument("--tsv", required=True)
    p.add_argument("--mapping", required=True)
    p.add_argument("--out")

    p = sub.add_parser("backup-write", help="write a Backup file")
    p.add_argument("--store", required=True)
    p.add_argument("--entries", required=True, help="JSON file of captured entries")
    p.add_argument("--out", required=True)

    p = sub.add_parser("backup-read", help="read a Backup into restore/delete sets")
    p.add_argument("--file", required=True)

    args = ap.parse_args(argv)

    if args.cmd == "rows":
        headers, rows = parse_tsv(_read(args.tsv))
        _emit({"headers": headers, "count": len(rows), "rows": rows})
        return 0

    if args.cmd == "inspect":
        headers, rows = parse_tsv(_read(args.tsv))
        mapping = json.loads(_read(args.mapping))
        tags = tag_inventory(rows, mapping)
        _, report = convert_rows(rows, mapping)
        missing = [c for t in mapping["targets"] for c in t["columns"]
                   if c not in headers]
        _emit({
            "headers": headers,
            "count": len(rows),
            "columns_not_in_sheet": missing,
            "tags": tags,
            "skipped": report["skipped"],
            "failures": report["failures"],
            "duplicate_handles": report["duplicate_handles"],
            "groups": report["groups"],
        })
        return 1 if (missing or tags["unsupported"] or report["failures"]) else 0

    if args.cmd == "convert":
        headers, rows = parse_tsv(_read(args.tsv))
        mapping = json.loads(_read(args.mapping))
        converted, report = convert_rows(rows, mapping)
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
