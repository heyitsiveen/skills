#!/usr/bin/env python3
"""
copy_template_content.py — Copy sections or blocks between Shopify JSON templates.

Used by the `shopify-copy-template-content` skill. See SKILL.md for invocation context.

Behavior:
  - Never modifies the source file.
  - Resolves source section/block names to keys via the `name` field, falling
    back to `type` (with case + hyphen/space normalization), then to the
    section key itself if the user passed it directly.
  - Aborts before opening any target file if any source name is unresolvable
    or ambiguous, so writes are atomic across all targets.
  - For each target: skips items whose key already exists, otherwise inserts
    into the container object AND the order array, right after the named anchor.
  - Preserves Shopify's leading /* ... */ comment header on write.
  - Preserves the 2-space indent + trailing newline Shopify uses.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Shopify wraps templates in a `/* ... */` comment header. JSON.parse rejects it.
HEADER_RE = re.compile(r"^\s*/\*[\s\S]*?\*/\s*")


def split_header(raw: str):
    """Return (header, json_text). Header is empty string if no /* ... */ prefix."""
    m = HEADER_RE.match(raw)
    if not m:
        return "", raw
    return m.group(0), raw[m.end():]


def read_template(path: Path):
    """Read a Shopify JSON template. Return (header, data) tuple."""
    raw = path.read_text(encoding="utf-8")
    header, json_text = split_header(raw)
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        die(f"Failed to parse JSON in {path}: {e}")
    return header, data


def write_template(path: Path, header: str, data: dict):
    """Write a Shopify JSON template with header preserved, 2-space indent, trailing newline."""
    body = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(header + body + "\n", encoding="utf-8")


def normalize(s: str) -> str:
    """Lower-case + replace whitespace with hyphens, so 'Scrolling text' ~= 'scrolling-text'."""
    return re.sub(r"\s+", "-", s.strip().lower()) if s else ""


def soft_match(user_name: str, entry_name: str, entry_type: str, entry_key: str) -> bool:
    """
    Return True if `user_name` plausibly refers to the entry with the given name/type/key.
    Permissive on purpose: Shopify types are kebab-case (`apps`, `scrolling-text`) while
    users use natural English ("App wrapper", "Scrolling text"). Soft-match bridges that.
    """
    if not user_name:
        return False
    if entry_name == user_name or entry_type == user_name or entry_key == user_name:
        return True
    if entry_name and entry_name.lower() == user_name.lower():
        return True
    nu, nn, nt = normalize(user_name), normalize(entry_name), normalize(entry_type)
    if not nu:
        return False
    if (nn and nu == nn) or (nt and nu == nt):
        return True
    if nn and (nu in nn or nn in nu):
        return True
    if nt and (nu in nt or nt in nu):
        return True
    # First-word soft match e.g. "App wrapper" → "apps"
    first_word = nu.split("-")[0]
    return bool(first_word and ((nn and first_word in nn) or (nt and first_word in nt)))


def resolve_single(container: dict, order: list, name: str):
    """
    Resolve a single `name` to a key. Used for anchors and unambiguous lookups.
    Returns the key or None. If multiple soft-matches exist, returns the FIRST in order.
    """
    if name in container:
        return name
    # Exact name match wins
    for key, entry in container.items():
        if entry.get("name") == name:
            return key
    # Soft match, iterating in `order` so the result is deterministic
    for key in order:
        if key in container and soft_match(name, container[key].get("name", ""),
                                           container[key].get("type", ""), key):
            return key
    # Fall back to any unordered entry
    for key, entry in container.items():
        if soft_match(name, entry.get("name", ""), entry.get("type", ""), key):
            return key
    return None


def select_sequence_after_anchor(container: dict, order: list, requested_names: list,
                                 anchor_name: str, container_label: str = "section"):
    """
    Resolve `requested_names` to N consecutive keys in `order`, starting right after
    the anchor. Sanity-check each (name, key) pair via soft_match. Honors user intent
    ("N items after X") over strict name lookup so users don't need to know the
    technical `type` strings.
    """
    anchor_key = resolve_single(container, order, anchor_name)
    if anchor_key is None:
        die(f"Anchor {anchor_name!r} not found in source.")
    if anchor_key not in order:
        die(f"Anchor {anchor_name!r} (key {anchor_key}) is in {container_label}s but not "
            f"in the order array — refusing to act on a malformed template.")
    anchor_idx = order.index(anchor_key)
    candidate_keys = order[anchor_idx + 1 : anchor_idx + 1 + len(requested_names)]
    if len(candidate_keys) < len(requested_names):
        die(f"Source has only {len(candidate_keys)} {container_label}(s) after anchor "
            f"{anchor_name!r}, but {len(requested_names)} were requested.")
    mismatches = []
    for req_name, key in zip(requested_names, candidate_keys):
        entry = container.get(key, {})
        if not soft_match(req_name, entry.get("name", ""), entry.get("type", ""), key):
            mismatches.append(
                f"  Requested {req_name!r} but next {container_label} is "
                f"{key!r} (name={entry.get('name', '<unset>')!r}, type={entry.get('type', '<unset>')!r})"
            )
    if mismatches:
        die(f"Sequence mismatch — names don't match the {container_label}s after "
            f"anchor {anchor_name!r}:\n" + "\n".join(mismatches) +
            f"\nIf you want these {container_label}s anyway, pass their exact keys.")
    return list(candidate_keys)


def select_by_name(container: dict, order: list, name: str):
    """
    Resolve a single requested name to a key when there's no From Position to scope by.
    Returns the key or raises SystemExit if 0 or >1 matches.
    """
    if name in container:
        return name
    # Exact name match
    exact_name = [k for k, e in container.items() if e.get("name") == name]
    if len(exact_name) == 1:
        return exact_name[0]
    if len(exact_name) > 1:
        die(f"Multiple sections share name {name!r}: {exact_name}. "
            f"Pass --from-position-after to disambiguate.")
    # Soft match across order
    soft = [k for k in order
            if k in container and soft_match(name, container[k].get("name", ""),
                                             container[k].get("type", ""), k)]
    if len(soft) == 1:
        return soft[0]
    if len(soft) > 1:
        die(f"Multiple soft-matches for {name!r}: {soft}. "
            f"Pass --from-position-after to disambiguate.")
    candidates = "\n  ".join(f"{k}: name={c.get('name', '<unset>')!r} type={c.get('type', '<unset>')!r}"
                             for k, c in container.items())
    die(f"Could not find section/block named {name!r}. Available entries:\n  {candidates}")


def die(msg: str):
    """Print an error to stderr and exit non-zero."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def insert_after(d: dict, key: str, new_key: str, new_value):
    """
    Insert (new_key, new_value) into the ordered dict `d` immediately after `key`.
    If `key` is not in `d`, append to the end.
    """
    rebuilt = {}
    inserted = False
    for k, v in d.items():
        rebuilt[k] = v
        if k == key and not inserted:
            rebuilt[new_key] = new_value
            inserted = True
    if not inserted:
        rebuilt[new_key] = new_value
    d.clear()
    d.update(rebuilt)


def insert_order_after(order: list, anchor_key: str, new_key: str):
    """Insert new_key into the order array immediately after anchor_key. Append if anchor missing."""
    try:
        idx = order.index(anchor_key)
        order.insert(idx + 1, new_key)
    except ValueError:
        order.append(new_key)


def copy_sections(src_data, target_path, target_data, resolved_keys,
                  to_position_after):
    """
    Copy already-resolved section keys from src_data to target_data.
    Returns (modified_bool, skipped_list, warnings_list).
    """
    src_sections = src_data.get("sections", {})
    tgt_sections = target_data.get("sections", {})
    tgt_order = target_data.get("order", [])

    # Resolve the target anchor BEFORE writing
    anchor_key = resolve_single(tgt_sections, tgt_order, to_position_after)
    if anchor_key is None:
        die(f"Target {target_path}: anchor {to_position_after!r} not found.")
    if anchor_key not in tgt_order:
        die(f"Target {target_path}: anchor {to_position_after!r} (key {anchor_key}) "
            f"is in sections but not in the order array — refusing to insert into a "
            f"template with a malformed order.")

    # Now do the inserts. When an item is already present (skipped), advance the
    # chaining cursor to its existing position — so a fresh item added later in the
    # list threads in after the existing chain, not between the anchor and the chain.
    skipped = []
    modified = False
    last_inserted_key = anchor_key
    for src_key in resolved_keys:
        if src_key in tgt_sections:
            skipped.append(f"{src_key} already exists in target")
            if src_key in tgt_order:
                last_inserted_key = src_key
            continue
        section_value = json.loads(json.dumps(src_sections[src_key]))  # deep copy
        insert_after(tgt_sections, last_inserted_key, src_key, section_value)
        insert_order_after(tgt_order, last_inserted_key, src_key)
        last_inserted_key = src_key
        modified = True

    target_data["sections"] = tgt_sections
    target_data["order"] = tgt_order
    return modified, skipped, []


def copy_blocks(src_data, target_path, target_data, resolved_keys,
                to_position_after, parent_section_name):
    """
    Copy already-resolved block keys from a parent section in src_data to the same-named
    parent section in target_data.
    """
    src_sections = src_data.get("sections", {})
    src_order = src_data.get("order", [])
    src_parent_key = resolve_single(src_sections, src_order, parent_section_name)
    if src_parent_key is None:
        die(f"Source parent section {parent_section_name!r} not found.")
    src_blocks = src_sections[src_parent_key].get("blocks", {})

    tgt_sections = target_data.get("sections", {})
    tgt_order = target_data.get("order", [])
    tgt_parent_key = resolve_single(tgt_sections, tgt_order, parent_section_name)
    if tgt_parent_key is None:
        die(f"Target {target_path}: parent section {parent_section_name!r} not found.")
    tgt_blocks = tgt_sections[tgt_parent_key].setdefault("blocks", {})
    tgt_block_order = tgt_sections[tgt_parent_key].setdefault("block_order", list(tgt_blocks.keys()))

    # Resolve target anchor
    anchor_key = resolve_single(tgt_blocks, tgt_block_order, to_position_after)
    if anchor_key is None:
        die(f"Target {target_path}: block anchor {to_position_after!r} not found.")
    if anchor_key not in tgt_block_order:
        die(f"Target {target_path}: block anchor {to_position_after!r} is in blocks "
            f"but not in block_order — refusing to insert.")

    skipped = []
    modified = False
    last_inserted_key = anchor_key
    for src_key in resolved_keys:
        if src_key in tgt_blocks:
            skipped.append(f"block {src_key} already exists in target parent section {tgt_parent_key}")
            if src_key in tgt_block_order:
                last_inserted_key = src_key
            continue
        block_value = json.loads(json.dumps(src_blocks[src_key]))  # deep copy
        insert_after(tgt_blocks, last_inserted_key, src_key, block_value)
        insert_order_after(tgt_block_order, last_inserted_key, src_key)
        last_inserted_key = src_key
        modified = True

    tgt_sections[tgt_parent_key]["blocks"] = tgt_blocks
    tgt_sections[tgt_parent_key]["block_order"] = tgt_block_order
    target_data["sections"] = tgt_sections
    return modified, skipped, []


def parse_csv(s: str):
    """Parse a comma-separated string, handling quoted values with embedded commas."""
    if not s:
        return []
    # Simple CSV: split on commas, strip whitespace and surrounding quotes
    items = []
    for raw in re.split(r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", s):
        item = raw.strip().strip('"').strip("'").strip()
        if item:
            items.append(item)
    return items


def main():
    ap = argparse.ArgumentParser(description="Copy sections or blocks between Shopify JSON templates.")
    ap.add_argument("--from", dest="src", required=True, help="Source template file path")
    ap.add_argument("--to", required=True, help="Comma-separated list of target template file paths")
    ap.add_argument("--sections", help="Comma-separated section names to copy (Format A)")
    ap.add_argument("--blocks", help="Comma-separated block names to copy (Format B)")
    ap.add_argument("--parent-section", help="For --blocks mode: name of the section whose blocks are being copied")
    ap.add_argument("--from-position-after", help="Anchor in source for disambiguation (optional)")
    ap.add_argument("--to-position-after", required=True, help="Anchor in each target for insertion")
    args = ap.parse_args()

    if bool(args.sections) == bool(args.blocks):
        die("Pass exactly one of --sections or --blocks.")

    src_path = Path(args.src.lstrip("@"))
    if not src_path.exists():
        die(f"Source file not found: {src_path}")

    target_paths = [Path(p.strip().lstrip("@")) for p in args.to.split(",") if p.strip()]
    for p in target_paths:
        if not p.exists():
            die(f"Target file not found: {p}")
        if p.resolve() == src_path.resolve():
            die(f"Target {p} is the same as source — refusing to modify source.")

    src_header, src_data = read_template(src_path)

    requested_names = parse_csv(args.sections or args.blocks)
    if not requested_names:
        die("No sections/blocks provided to copy.")

    summary = {"modified": [], "skipped": {}, "warnings": []}

    # Phase 1: resolve EVERY requested name in the source to a concrete key.
    # Abort before opening any target if resolution fails or sequence-checks fail.
    src_sections = src_data.get("sections", {})
    src_order = src_data.get("order", [])

    if args.sections:
        if args.from_position_after:
            resolved_source_keys = select_sequence_after_anchor(
                src_sections, src_order, requested_names, args.from_position_after, "section")
        else:
            resolved_source_keys = [select_by_name(src_sections, src_order, n) for n in requested_names]
    else:
        if not args.parent_section:
            die("--parent-section is required when copying blocks "
                "(use the parent section's name from the source).")
        parent_key = resolve_single(src_sections, src_order, args.parent_section)
        if parent_key is None:
            die(f"Source parent section {args.parent_section!r} not found.")
        parent_blocks = src_sections[parent_key].get("blocks", {})
        parent_block_order = src_sections[parent_key].get("block_order", list(parent_blocks.keys()))
        if args.from_position_after:
            resolved_source_keys = select_sequence_after_anchor(
                parent_blocks, parent_block_order, requested_names, args.from_position_after, "block")
        else:
            resolved_source_keys = [select_by_name(parent_blocks, parent_block_order, n)
                                    for n in requested_names]

    # Phase 2: apply to each target
    for tgt_path in target_paths:
        tgt_header, tgt_data = read_template(tgt_path)
        if args.sections:
            modified, skipped, warnings = copy_sections(
                src_data, str(tgt_path), tgt_data, resolved_source_keys,
                args.to_position_after)
        else:
            modified, skipped, warnings = copy_blocks(
                src_data, str(tgt_path), tgt_data, resolved_source_keys,
                args.to_position_after, args.parent_section)

        if modified:
            write_template(tgt_path, tgt_header, tgt_data)
            summary["modified"].append(str(tgt_path))
        if skipped:
            summary["skipped"][str(tgt_path)] = skipped
        summary["warnings"].extend(warnings)

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
