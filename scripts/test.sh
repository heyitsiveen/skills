#!/usr/bin/env bash
#
# Run the repo's Python tests: every test file as its own unittest process,
# several files at once.
#
# A test file is a test*.py file outside deprecated/ and the hidden folders.
# Each one runs as
#
#     python3 -m unittest discover -s <its folder> -p <its name>
#
# which imports it exactly as a run of its whole folder would. Files run as
# many at a time as the machine has CPUs (TEST_JOBS overrides that), biggest
# first. Each file's output is printed under a `== <file>` header once the file
# has finished, and every file runs even after one fails.
#
#   ./scripts/test.sh                every test file in the repo
#   ./scripts/test.sh <folder>...    the test files under those folders
#
# Exits 0 when every file passed, and 1 when any failed or none was found.

set -uo pipefail

if [ "$#" -eq 0 ]; then
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd)"
  if [ -z "$ROOT" ] || ! cd "$ROOT"; then
    printf 'cannot resolve the repo root from %s\n' "${BASH_SOURCE[0]}" >&2
    exit 1
  fi
  set -- .
fi

jobs=${TEST_JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)}
case $jobs in
  '' | *[!0-9]* | 0)
    printf 'TEST_JOBS must be a whole number above 0, not "%s"\n' "$jobs" >&2
    exit 1
    ;;
esac

work=$(mktemp -d "${TMPDIR:-/tmp}/test-sh.XXXXXX") || exit 1
trap 'rm -rf "$work"' EXIT

# The test files, one per line: each folder's own rule, so deprecated/ and the
# hidden folders are those directly inside the folder searched. Biggest first:
# a big file tends to run longest, so it starts early rather than finishing last.
for folder in "$@"; do
  (cd "$folder" && find . \( -path './.*' -o -path ./deprecated \) -prune -o \
     -name 'test*.py' -print) |
    while IFS= read -r found; do
      if [ "$folder" = . ]; then
        printf '%s\n' "${found#./}"
      else
        printf '%s\n' "${folder%/}/${found#./}"
      fi
    done
done | while IFS= read -r file; do
  printf '%s %s\n' "$(($(wc -c <"$file")))" "$file"
done | sort -k1,1nr -k2 | cut -d' ' -f2- >"$work/files"

if [ ! -s "$work/files" ]; then
  printf 'no test*.py files under %s\n' "$*" >&2
  exit 1
fi

# One test file, run by xargs. Its output waits in a log until it has finished,
# then goes out whole under its header, one file at a time; a failure is noted
# in $work/failed.
run_one() {
  local file=$1 log
  log=$(mktemp "$work/log.XXXXXX") || return 1
  python3 -m unittest discover -s "$(dirname "$file")" -p "$(basename "$file")" \
    >"$log" 2>&1 || printf '%s\n' "$file" >>"$work/failed"
  until mkdir "$work/printing" 2>/dev/null; do sleep 0.1; done
  printf '== %s\n' "$file"
  cat "$log"
  rmdir "$work/printing"
}
export -f run_one
export work

tr '\n' '\0' <"$work/files" | xargs -0 -n 1 -P "$jobs" bash -c 'run_one "$1"' run_one
ran=$?

files=$(($(wc -l <"$work/files")))
if [ -s "$work/failed" ]; then
  printf '\n%d of %d test files failed:\n' "$(($(wc -l <"$work/failed")))" "$files"
  sort "$work/failed" | sed 's/^/  /'
  exit 1
fi
if [ "$ran" -ne 0 ]; then
  printf '\nnot every test file could be run: xargs exited %d\n' "$ran" >&2
  exit 1
fi
printf '\nAll %d test files passed.\n' "$files"
