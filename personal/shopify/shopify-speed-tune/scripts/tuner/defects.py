"""The known Golden theme defects: each one checked by its detection rule.

The entries, their proven fixes and their measured effects live in the skill's
`references/known-defects.md`, which is also where each entry's fixing Golden
version is recorded. This module reads that version from the reference and
applies the rules: repo rules to the client repo's working tree, after Liquid
comments are stripped (Golden keeps commented-out legacy copies of the image
snippet, comments nested inside), and the D2 page rule to each page's baseline
Samples.

A theme whose `theme_info` does not name Golden gets no check at all.
"""

import json
import os
import re

from tuner import probe
from tuner.output import Failed

REFERENCE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         "references", "known-defects.md")
ENTRIES = ("D1", "D2", "D3", "D4")
EAGER_ARGUMENTS = ("lazy_loading", "eager_load", "priority", "priority_loading", "fetchpriority")
COMMENT_TAG = re.compile(r"\{%-?\s*(end)?comment\s*-?%\}")
PAGE_MAJORITY = 3


def reference_path():
    return os.environ.get("SPEED_TUNE_KNOWN_DEFECTS") or REFERENCE


def fixed_versions():
    """{entry id: the first Golden version carrying its fix, or None}, from the reference."""
    path = reference_path()
    with open(path, encoding="utf-8") as f:
        text = f.read()
    sections = re.split(r"(?m)^## (D\d+)\. ", text)
    found = {}
    for entry, body in zip(sections[1::2], sections[2::2]):
        lines = re.findall(r"(?m)^\*\*Fixed in Golden:\*\*\s*(.*?)\s*$", body)
        if len(lines) != 1:
            raise Failed("bad-reference", "%s: entry %s needs exactly one **Fixed in Golden:** line"
                         % (path, entry))
        value = lines[0]
        if value.lower() in ("", "not yet"):
            found[entry] = None
        elif re.fullmatch(r"\d+(?:\.\d+)*", value):
            found[entry] = value
        else:
            raise Failed("bad-reference", "%s: entry %s's fixing version %r is not a version"
                         % (path, entry, value))
    missing = [e for e in ENTRIES if e not in found]
    if missing:
        raise Failed("bad-reference", "%s has no entry %s" % (path, ", ".join(missing)))
    return found


def _version(text):
    return tuple(int(part) for part in re.findall(r"\d+", text or ""))


def theme_info(root):
    """(name, version) from config/settings_schema.json's theme_info, or (None, None)."""
    try:
        with open(os.path.join(root, "config", "settings_schema.json"), encoding="utf-8") as f:
            schema = json.load(f)
    except (OSError, ValueError):
        return None, None
    for block in schema if isinstance(schema, list) else []:
        if isinstance(block, dict) and block.get("name") == "theme_info":
            return block.get("theme_name"), block.get("theme_version")
    return None, None


def strip_comments(text):
    """Liquid without its comments: nested comment blocks, `comment` lines inside a
    `{% liquid %}` tag, and inline `{% # … %}` tags."""
    kept, depth, last = [], 0, 0
    for tag in COMMENT_TAG.finditer(text):
        if tag.group(1) is None:
            if depth == 0:
                kept.append(text[last:tag.start()])
            depth += 1
        elif depth > 0:
            depth -= 1
            if depth == 0:
                last = tag.end()
    if depth == 0:
        kept.append(text[last:])
    text = "".join(kept)
    text = re.sub(r"(?ms)^\s*comment\s*$.*?^\s*endcomment\s*$", "", text)
    return re.sub(r"\{%-?\s*#[^%]*-?%\}", "", text)


def _read(root, path):
    try:
        with open(os.path.join(root, path), encoding="utf-8", errors="replace") as f:
            return strip_comments(f.read())
    except OSError:
        return None


def check(root, reports_by_page):
    """Run every entry's rule. Returns {"theme": {...}, "golden": bool, "results": [...]},
    each result {"id", "state": found | clear | skipped, "pages", "evidence"}."""
    name, version = theme_info(root)
    out = {"theme": {"name": name, "version": version}, "golden": name == "Golden", "results": []}
    if name != "Golden":
        return out
    fixed = fixed_versions()
    image = _read(root, "snippets/responsive-image.liquid")
    media = _read(root, "blocks/media.liquid")
    button = _read(root, "snippets/button.liquid")
    results = []

    def add(entry, hit, evidence, pages=()):
        if fixed.get(entry) and _version(version) >= _version(fixed[entry]):
            results.append({"id": entry, "state": "skipped", "pages": [],
                            "evidence": "fixed in Golden %s, and this theme is %s"
                                        % (fixed[entry], version)})
        else:
            results.append({"id": entry, "state": "found" if hit else "clear",
                            "pages": list(pages) if hit else [], "evidence": evidence if hit else ""})

    add("D1", image is not None and bool(re.search(
        r"assign\s+lazy_loading\s*=\s*lazy_loading\s*\|\s*default:\s*true(?!\s*,\s*allow_false:\s*true)",
        image)), "snippets/responsive-image.liquid defaults lazy_loading to true without allow_false")

    lazy_pages = []
    for page, reports in reports_by_page.items():
        count = sum(1 for r in reports if probe.lazy_lcp(r))
        if count >= PAGE_MAJORITY:
            lazy_pages.append((page, count, len(reports)))
    stub = image is not None and bool(re.search(r"image_url:\s*width:\s*20\b", image)) \
        and "data-src" in image
    calls = re.findall(r"\{%-?\s*render\s+'responsive-image'(.*?)-?%\}", media or "", re.S)
    hero = stub and bool(calls) and not any(
        re.search(r"\b(%s)\s*:" % "|".join(EAGER_ARGUMENTS), call) for call in calls)
    pages = [p for p, _, _ in lazy_pages]
    if hero and "home" not in pages:
        pages.insert(0, "home")
    evidence = []
    if lazy_pages:
        evidence.append("the LCP image waits for lazysizes in the baseline Samples of %s" % ", ".join(
            "%s (%d of %d)" % (page, count, total) for page, count, total in lazy_pages))
    if hero:
        evidence.append("blocks/media.liquid renders the hero with no loading argument")
    add("D2", bool(pages), "; ".join(evidence), pages)

    add("D3", image is not None and bool(re.search(r"slice:\s*0\s*,\s*srcset_clean_length", image))
        and "forloop.last" in image,
        "snippets/responsive-image.liquid slices the last width descriptor off its srcset")

    block = re.search(r"\{%-?\s*style\s*-?%\}(.*?)\{%-?\s*endstyle\s*-?%\}", button or "", re.S)
    add("D4", bool(block) and "{{" not in block.group(1) and len(block.group(1)) > 2000,
        "snippets/button.liquid repeats a %s-character static style block for every button"
        % ("{:,}".format(len(block.group(1))) if block else "0"))
    out["results"] = results
    return out


def lines(checked):
    """The DEFECT lines for a check's result."""
    theme = checked["theme"]
    if not checked["golden"]:
        if theme["name"]:
            return ['none: the theme is "%s" %s, not Golden' % (theme["name"], theme["version"] or "")]
        return ["none: config/settings_schema.json names no theme, so it is not Golden"]
    out = ["theme Golden %s" % theme["version"]]
    for result in checked["results"]:
        head = "%s %s" % (result["id"], result["state"])
        if result["state"] == "found" and result["id"] == "D2":
            head += " on %s" % ", ".join(result["pages"])
        out.append(head + (": %s" % result["evidence"] if result["evidence"] else ""))
    return out
