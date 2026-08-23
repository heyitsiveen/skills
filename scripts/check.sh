#!/usr/bin/env bash
#
# Assert this repo's cross-file invariants:
#
#   1. the two knowledge-doc format specs are byte-identical across the four
#      producer skills
#   2. `## Asset export` is byte-identical across the three Figma-driven skills
#   3. every skill is listed in all three registries — `deprecated/` is a
#      retained snapshot, not a bucket, so it is skipped by this assertion
#   4. the retired pixel-diff vocabulary appears in none of the three
#      Figma-driven skills, nor in the README
#   5. Phase 4's seven steps are present, in order, in each of the three
#   6. each of the three specifies the design spec's producer header
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

# The three Figma-driven skills, which share a `## Asset export` section and
# the seven-step Phase 4.
FIGMA_SKILLS=(figma-shopify-builder figma-shopify-composer shopify-app-restyle)

# Terms the design-spec convention retired. None may reappear in the three
# Figma-driven skills or in the README. Each is a POSIX ERE, deliberately wider
# than the literal wording the tickets used: the hyphenated spellings are this
# repo's own house style, so they are the likeliest form of a relapse, and the
# diff-image names are generalised past the two breakpoints that existed.
BANNED_TERMS=(
  'diff-[a-z]+\.png'
  'pixelmatch'
  'odiff'
  'visual[- ]verifier'
  'pixel[- ]diff'
  'never[- ]eyeballed'
)

# Phase 4's seven steps, in order, as `<pattern>::<name>`: the ERE that marks
# the step, and the name a failure reports. One array, so the two cannot
# desync; `::` is the delimiter because the EREs use `|` for alternation.
PHASE4_STEPS=(
  '^\*\*1\. Render\.\*\*::1. Render'
  '^\*\*2\. Data check\*\*::2. Data check'
  '^\*\*3\. Capture hygiene\*\*::3. Capture hygiene'
  '^\*\*4\. `style-reporter`,::4. `style-reporter`'
  '^\*\*5\. Correction round\*\*::5. Correction round'
  '^\*\*6\. Style report(\.\*\*| —)::6. Style report'
  '^\*\*7\. Cleanup\.\*\*::7. Cleanup'
)

# No eighth step: the shape is seven, and CLAUDE.md calls a fourth variation a
# rule break. An added step would otherwise pass the in-order scan unnoticed.
PHASE4_NO_EIGHTH='^\*\*8\.'

# The one-line summary of the shape, which all three carry verbatim.
PHASE4_CHAIN='render → data check → capture hygiene → `style-reporter` → correction round → style report → cleanup'

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
# 2. `## Asset export` is byte-identical across the three Figma-driven skills
# ---------------------------------------------------------------------------

# extract_section <heading-regex> <file>
# Print one `## …` section of a SKILL.md, heading included, up to (not
# including) the next `## ` heading.
extract_section() {
  awk -v heading="$1" '
    $0 ~ heading    { inside = 1; print; next }
    inside && /^## / { exit }
    inside           { print }
  ' "$2"
}

check_asset_export() {
  local tmp base base_label path skill
  tmp="$(mktemp -d)" || { fail "cannot create a temp dir for the '## Asset export' comparison"; return; }

  base=""
  base_label=""
  for skill in "${FIGMA_SKILLS[@]}"; do
    path="personal/shopify/$skill/SKILL.md"
    require_file "$path" || continue
    extract_section '^## Asset export' "$path" > "$tmp/$skill"
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
      "'## Asset export' must be byte-identical across the three Figma-driven skills"
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
             -not -path './.git/*' -not -path './.scratch/*' \
             -not -path './deprecated/*' | sort)
}

# ---------------------------------------------------------------------------
# 4. The retired pixel-diff vocabulary appears nowhere
# ---------------------------------------------------------------------------

check_banned_terms() {
  local term target hits status line skill
  local targets=("$README")

  for skill in "${FIGMA_SKILLS[@]}"; do
    targets+=("personal/shopify/$skill")
  done

  for target in "${targets[@]}"; do
    if [ ! -e "$target" ]; then
      fail "missing path: $target"
      continue
    fi
    for term in "${BANNED_TERMS[@]}"; do
      hits="$(grep -rnE -- "$term" "$target")"
      status=$?
      # 0 = matched, 1 = no match, anything else = grep itself failed. Without
      # this the check would pass silently on a malformed pattern.
      if [ "$status" -gt 1 ]; then
        fail "cannot scan $target for the retired term '$term' (grep exited $status)"
        continue
      fi
      [ "$status" -eq 0 ] || continue
      while IFS= read -r line; do
        fail "$target still uses the retired term '$term' — $line"
      done <<< "$hits"
    done
  done
}

# ---------------------------------------------------------------------------
# 5. Phase 4's seven steps are present, in order, in each Figma-driven skill
# ---------------------------------------------------------------------------

check_phase4_shape() {
  local skill path section i total line

  total=${#PHASE4_STEPS[@]}

  for skill in "${FIGMA_SKILLS[@]}"; do
    path="personal/shopify/$skill/SKILL.md"
    require_file "$path" || continue

    section="$(extract_section '^## Phase 4' "$path")"
    if [ -z "$section" ]; then
      fail "$path has no '## Phase 4' section"
      continue
    fi

    i=0
    while IFS= read -r line; do
      [ "$i" -lt "$total" ] || break
      if printf '%s\n' "$line" | grep -qE -- "${PHASE4_STEPS[$i]%%::*}"; then
        i=$((i + 1))
      fi
    done <<< "$section"

    if [ "$i" -lt "$total" ]; then
      fail "$path: Phase 4 step '${PHASE4_STEPS[$i]##*::}' is missing or out of order (found $i of $total steps in sequence)"
    fi

    if printf '%s\n' "$section" | grep -qE -- "$PHASE4_NO_EIGHTH"; then
      fail "$path: Phase 4 has an eighth step — the shared shape is seven"
    fi

    printf '%s\n' "$section" | grep -qF -- "$PHASE4_CHAIN" ||
      fail "$path: Phase 4 does not state the seven-step chain verbatim ($PHASE4_CHAIN)"

    grep -qF -- 'style-reporter' "$path" ||
      fail "$path does not mention 'style-reporter'"
  done
}

# ---------------------------------------------------------------------------
# 6. Each Figma-driven skill specifies the design spec's producer header
# ---------------------------------------------------------------------------

check_producer_header() {
  local skill path

  for skill in "${FIGMA_SKILLS[@]}"; do
    path="personal/shopify/$skill/SKILL.md"
    require_file "$path" || continue

    grep -qE "^[[:space:]]+producer: $skill — write surface:" "$path" ||
      fail "$path does not specify the design spec's producer header (expected a line 'producer: $skill — write surface: …')"

    grep -qF -- 'Open the document with this header line, verbatim' "$path" ||
      fail "$path does not instruct the extractor to open the design spec with the producer header verbatim"
  done
}

check_format_specs
check_asset_export
check_registries
check_banned_terms
check_phase4_shape
check_producer_header

if [ "$FAILURES" -ne 0 ]; then
  printf '\n%d check(s) failed.\n' "$FAILURES" >&2
  exit 1
fi

printf 'All checks passed.\n'
