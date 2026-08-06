#!/usr/bin/env bash
#
# Assert this repo's cross-file invariants.
#
# Run from anywhere; it resolves the repo root itself.
#   ./scripts/check.sh
#
# Exits 0 when every assertion holds. Otherwise it prints one FAIL line per
# broken assertion, naming the offending path, and exits 1.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd)"
if [ -z "$ROOT" ] || ! cd "$ROOT"; then
  printf 'FAIL: cannot resolve the repo root from %s\n' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

README=README.md
SKILLS_SH=skills.sh.json
MARKETPLACE=.claude-plugin/marketplace.json

# The four skills that produce the shared knowledge-doc format specs.
PRODUCERS=(client-theme-onboarding figma-shopify-builder figma-shopify-composer figma-shopify-globals)

# The three Figma-measuring skills, which share a `## Asset export` section.
FIGMA_SKILLS=(figma-shopify-builder figma-shopify-composer shopify-app-restyle)

FAILURES=0

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  FAILURES=$((FAILURES + 1))
}

# require_file <path> -> 0 if present, 1 (with a FAIL) if not
require_file() {
  if [ ! -f "$1" ]; then
    fail "missing file: $1"
    return 1
  fi
  return 0
}

# compare_to_base <base-label> <base-file> <other-label> <other-file> <rule>
# The labels are what a failure names; the files are what is actually compared,
# which for an extracted section is not the same thing.
compare_to_base() {
  cmp -s "$2" "$4" || fail "$3 differs from $1 ($5)"
}

# ---------------------------------------------------------------------------
# 1. Format specs are byte-identical across the four knowledge-doc producers
# ---------------------------------------------------------------------------

check_format_specs() {
  local spec base other skill
  for spec in theme-capabilities-format.md components-format.md; do
    base="personal/shopify/${PRODUCERS[0]}/references/$spec"
    require_file "$base" || continue
    for skill in "${PRODUCERS[@]:1}"; do
      other="personal/shopify/$skill/references/$spec"
      require_file "$other" || continue
      compare_to_base "$base" "$base" "$other" "$other" \
        "references/$spec must be byte-identical across the four producers"
    done
  done
}

# ---------------------------------------------------------------------------
# 2. `## Asset export` is byte-identical across the three Figma-measuring skills
# ---------------------------------------------------------------------------

# Print the `## Asset export …` section of a SKILL.md: from its heading up to
# (not including) the next `## ` heading.
extract_asset_export() {
  awk '
    /^## Asset export/ { inside = 1; print; next }
    inside && /^## /   { exit }
    inside             { print }
  ' "$1"
}

check_asset_export() {
  local tmp base base_label path skill
  tmp="$(mktemp -d)" || { fail "cannot create a temp dir for the '## Asset export' comparison"; return; }

  base=""
  base_label=""
  for skill in "${FIGMA_SKILLS[@]}"; do
    path="personal/shopify/$skill/SKILL.md"
    require_file "$path" || continue
    extract_asset_export "$path" > "$tmp/$skill"
    if [ ! -s "$tmp/$skill" ]; then
      fail "$path has no '## Asset export' section"
      continue
    fi
    if [ -z "$base" ]; then
      base="$tmp/$skill"
      base_label="$path"
      continue
    fi
    compare_to_base "$base_label" "$base" "$path" "$tmp/$skill" \
      "'## Asset export' must be byte-identical across the three Figma-measuring skills"
  done

  rm -rf "$tmp"
}

# ---------------------------------------------------------------------------
# 3. Every skill directory is listed in all three registries
# ---------------------------------------------------------------------------

# Print one `<bucket>\t<domain>/<name>` line per skill entry in the marketplace,
# so the membership check knows which plugin each path was published under.
# The marketplace is small and hand-maintained; a format change that breaks this
# reader is caught by the "no skill entries" failure below rather than passing
# silently.
marketplace_entries() {
  awk '
    /"name"[[:space:]]*:[[:space:]]*"heyitsiveen-skills-/ {
      plugin = $0
      sub(/.*"heyitsiveen-skills-/, "", plugin)
      sub(/".*/, "", plugin)
      next
    }
    /"skills"[[:space:]]*:/ { if ($0 !~ /\]/) inside = 1; next }
    inside && /\]/         { inside = 0; next }
    inside && /"\.\// {
      entry = $0
      sub(/.*"\.\//, "", entry)
      sub(/".*/, "", entry)
      print plugin "\t" entry
    }
  ' "$1"
}

# Print one bucket name per published plugin, from its `"source": "./<bucket>"`.
# A bucket with an empty `skills` array is still published, so this is read
# separately from the skill entries above.
marketplace_buckets() {
  awk '
    /"source"[[:space:]]*:[[:space:]]*"\.\// {
      bucket = $0
      sub(/.*"\.\//, "", bucket)
      sub(/".*/, "", bucket)
      print bucket
    }
  ' "$1" | sort -u
}

check_registries() {
  local skill_md dir bucket domain name entries buckets

  require_file "$README" || return
  require_file "$SKILLS_SH" || return
  require_file "$MARKETPLACE" || return

  buckets="$(marketplace_buckets "$MARKETPLACE")"
  entries="$(marketplace_entries "$MARKETPLACE")"
  if [ -z "$buckets" ] || [ -z "$entries" ]; then
    fail "$MARKETPLACE lists no buckets or no skills under any heyitsiveen-skills-* plugin (unreadable or empty)"
    return
  fi

  while IFS= read -r skill_md; do
    dir="${skill_md#./}"
    dir="$(dirname "$dir")"          # <bucket>/<domain>/<name>
    bucket="${dir%%/*}"
    name="${dir##*/}"
    domain="${dir#"$bucket"/}"
    domain="${domain%/"$name"}"

    if ! printf '%s\n' "$buckets" | grep -qx "$bucket"; then
      fail "$dir sits in bucket '$bucket', which no heyitsiveen-skills-* plugin publishes"
      continue
    fi

    grep -qF "./$dir/SKILL.md" "$README" ||
      fail "$README does not link $dir (expected a link to ./$dir/SKILL.md)"

    grep -qE "^[[:space:]]*\"$name\",?$" "$SKILLS_SH" ||
      fail "$SKILLS_SH does not list \"$name\" ($dir)"

    printf '%s\n' "$entries" | grep -qxF "$bucket	$domain/$name" ||
      fail "$MARKETPLACE does not list \"./$domain/$name\" under plugin heyitsiveen-skills-$bucket ($dir)"
  done < <(find . -mindepth 4 -maxdepth 4 -name SKILL.md \
             -not -path './.git/*' -not -path './.scratch/*' | sort)
}

check_format_specs
check_asset_export
check_registries

if [ "$FAILURES" -ne 0 ]; then
  printf '\n%d check(s) failed.\n' "$FAILURES" >&2
  exit 1
fi

printf 'All checks passed.\n'
