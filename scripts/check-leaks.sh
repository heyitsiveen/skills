#!/usr/bin/env bash
#
# Refuse client identifiers in this public repo.
#
# The identifiers are listed in `.leak-denylist` at the repo root, which is
# gitignored: the list names every client, so committing it would be the leak.
# One fixed string per line, matched in any letter case. Blank lines, lines
# whose first non-blank character is `#`, and whitespace around an entry are
# ignored. A linked worktree reads its own `.leak-denylist` and the main
# checkout's, so one file at the clone's root covers every worktree.
#
#   scripts/check-leaks.sh         scan the lines the index adds (pre-commit)
#   scripts/check-leaks.sh --all   scan every tracked file (before a push)
#
# Exits 0 when no entry matches, and when there is no denylist (CI, a fresh
# clone), after a one-line note. Otherwise it prints one FAIL line per hit,
# naming file:line and the text that matched, and exits 1.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd)"
if [ -z "$ROOT" ] || ! cd "$ROOT"; then
  printf 'FAIL: cannot resolve the repo root from %s\n' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

DENYLIST=.leak-denylist

case "${1-}" in
  '')    MODE=staged ;;
  --all) MODE=all ;;
  *)     printf 'usage: %s [--all]\n' "$0" >&2; exit 2 ;;
esac

# denylists
# Print the path of each denylist this checkout reads: its own, then the main
# checkout's when this is a linked worktree. `git worktree add` copies no
# ignored file, so without the second a new worktree would check nothing.
denylists() {
  local main
  [ -f "$DENYLIST" ] && printf '%s\n' "$ROOT/$DENYLIST"
  # The main worktree is always listed first.
  main="$(git worktree list --porcelain 2>/dev/null | sed -n '1s/^worktree //p')"
  if [ -n "$main" ] && [ -f "$main/$DENYLIST" ] && ! [ "$main/$DENYLIST" -ef "$DENYLIST" ]; then
    printf '%s\n' "$main/$DENYLIST"
  fi
}

# entries <denylist>...
# Print each entry once, trimmed, without the comments and blank lines.
entries() {
  awk '
    { sub(/\r$/, ""); sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+$/, "") }
    $0 == "" || substr($0, 1, 1) == "#" { next }
    !seen[tolower($0)]++
  ' "$@"
}

# staged_hits <entries-file>
# Print `<file>:<line>:<entry>` for each entry in a line the index adds.
staged_hits() {
  local base=HEAD
  # Before the first commit there is no HEAD: diff against the empty tree.
  git rev-parse -q --verify HEAD >/dev/null || base="$(git hash-object -t tree /dev/null)"
  git diff-index --cached -p -U0 -M "$base" |
    awk -v entries="$1" '
      BEGIN {
        while ((getline entry < entries) > 0) { n++; shown[n] = entry; wanted[n] = tolower(entry) }
      }
      /^diff --git / { header = 1; next }
      # `+++ b/<path>`: git appends a tab to a path with a space, and quotes
      # one with an unusual character.
      header && /^\+\+\+ / {
        file = substr($0, 5)
        sub(/\t$/, "", file)
        if (file ~ /^".*"$/) file = substr(file, 2, length(file) - 2)
        sub(/^b\//, "", file)
        next
      }
      /^@@ / {
        header = 0
        match($0, /\+[0-9]+/)
        line = substr($0, RSTART + 1, RLENGTH - 1) + 0
        next
      }
      header { next }
      /^\+/ {
        text = tolower(substr($0, 2))
        for (i = 1; i <= n; i++)
          if (index(text, wanted[i])) print file ":" line ":" shown[i]
        line++
        next
      }
      /^ / { line++ }
    '
}

# all_hits <entries-file>
# Print `<file>:<line>:<text>` for each entry in a tracked file, <text> being
# the matched text as the file spells it.
all_hits() {
  local status
  git grep --no-color --no-column -n -o -I -i -F -f "$1"
  status=$?
  # 0 = matched, 1 = no match, anything else = git grep itself failed.
  [ "$status" -le 1 ] || return "$status"
}

ENTRIES="$(mktemp)" || { printf 'FAIL: cannot create a temp file for the denylist\n' >&2; exit 1; }
trap 'rm -f "$ENTRIES"' EXIT

lists="$(denylists)"
if [ -n "$lists" ]; then
  files=()
  while IFS= read -r list; do files+=("$list"); done <<< "$lists"
  entries "${files[@]}" > "$ENTRIES"
fi

if [ ! -s "$ENTRIES" ]; then
  printf 'NOTE: no %s entries in this checkout or the main one, so client identifiers are not checked.\n' "$DENYLIST"
  exit 0
fi

if [ "$MODE" = all ]; then
  scope='the tracked files'
  hits="$(all_hits "$ENTRIES")"
else
  scope='the staged lines'
  hits="$(staged_hits "$ENTRIES")"
fi
status=$?
if [ "$status" -ne 0 ]; then
  printf 'FAIL: cannot scan %s for %s entries (exit %s)\n' "$scope" "$DENYLIST" "$status" >&2
  exit 1
fi

if [ -z "$hits" ]; then
  printf 'No %s entry in %s.\n' "$DENYLIST" "$scope"
  exit 0
fi

# Each hit is `<file>:<line>:<text>`. Split at the first two colons: a path
# could hold one, but none of this repo's do, and the text may.
count=0
while IFS= read -r hit; do
  file="${hit%%:*}"
  rest="${hit#*:}"
  printf "FAIL: %s:%s names '%s', a %s entry\n" "$file" "${rest%%:*}" "${rest#*:}" "$DENYLIST" >&2
  count=$((count + 1))
done <<< "$hits"

printf '\n%d hit(s) in %s. This repo is public: replace each with a placeholder or a neutral reference, or drop the entry from %s if it names no client.\n' \
  "$count" "$scope" "$DENYLIST" >&2
exit 1
