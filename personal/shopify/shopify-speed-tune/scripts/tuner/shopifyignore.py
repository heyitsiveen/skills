"""The repo's .shopifyignore, read the way Shopify CLI 4.8 reads it before a push.

The CLI drops every file a .shopifyignore line matches from what a push uploads
and what it deletes, even a file named in --only, and says nothing. A Round's
change to such a file never reaches the theme, so the Round would measure
nothing: the guarded write refuses it.

How the CLI reads the file (4.8.5, `applyIgnoreFilters`):
- lines are trimmed; blank lines and lines starting with # are skipped
- a line is a glob, matched by minimatch with matchBase and noglobstar: a glob
  without a slash matches the file's name in any folder, `**` matches within
  one folder like `*`, `{a,b}` gives alternatives, and a wildcard never
  matches a name's leading dot
- a glob ending in `templates/*`, `templates/*.json` or `templates/*.liquid`
  also matches one folder deeper, such as templates/customers/
- a line wrapped in slashes is also tried as a regular expression, anywhere in
  the path
- a line starting with ! puts every file it matches back into the push, past
  --only, so a push could send or delete files the Round never changed

The program refuses that last kind of line, and any glob form it cannot match
the way the CLI does (extglobs such as +(a|b), POSIX classes, brace ranges),
rather than guess.
"""

import os
import re

from tuner.output import Refused

FILE = ".shopifyignore"
TEMPLATES = re.compile(r"templates/\*(\.(json|liquid))?$")
UNSUPPORTED = re.compile(r"[@!?*+]\(|\[:|\{[^{}]*\.\.[^{}]*\}")


def lines(root):
    """[(line number, pattern)] of the repo's .shopifyignore, as the CLI keeps them."""
    path = os.path.join(root, FILE)
    if not os.path.isfile(path):
        return []
    # utf-8-sig drops a byte-order mark, as the CLI's trim() does.
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        text = f.read()
    found = []
    for number, line in enumerate(re.split(r"\r\n|\r|\n", text), 1):
        line = line.strip()
        if line and not line.startswith("#"):
            found.append((number, line))
    return found


def check(root, paths):
    """Refuse unless the CLI would push every one of `paths`, and only those."""
    patterns = lines(root)
    for number, pattern in patterns:
        if pattern.startswith("!"):
            raise Refused("shopifyignore-negation",
                          "%s line %d (%s) puts the files it matches back into every push, past "
                          "its exact --only paths, so a push could change files the Round did not"
                          % (FILE, number, pattern),
                          "Show the developer this line: the program pushes exact paths only.")
        readable = regex_ok(pattern) if is_regex(pattern) else not UNSUPPORTED.search(pattern)
        if not readable:
            raise Refused("shopifyignore-unreadable",
                          "%s line %d (%s) uses a pattern form the program cannot match the way "
                          "the CLI does" % (FILE, number, pattern),
                          "Show the developer this line: the program refuses rather than guess "
                          "which files the CLI would skip.")
    for path in paths:
        for number, pattern in patterns:
            if matches(path, pattern):
                raise Refused("shopifyignore",
                              "%s is excluded by %s line %d (%s), so the CLI would skip it "
                              "silently and the Round would measure nothing"
                              % (path, FILE, number, pattern),
                              "Take that file out of the change and push again. When the plan "
                              "item cannot be made without it, run `verdict --remove`; the %s "
                              "is the developer's to change." % FILE)


def is_regex(pattern):
    return pattern.startswith("/") and pattern.endswith("/")


def regex_ok(pattern):
    try:
        re.compile(pattern[1:-1])
        return True
    except re.error:
        return False


def matches(path, pattern):
    """Whether the CLI drops `path` for the .shopifyignore line `pattern`."""
    if glob(path, pattern):
        return True
    if TEMPLATES.search(pattern) and glob(path, TEMPLATES.sub(r"templates/**/*\1", pattern, 1)):
        return True
    return is_regex(pattern) and re.search(pattern[1:-1], path) is not None


def glob(path, pattern):
    """minimatch(path, pattern, {matchBase: true, noglobstar: true}), for the forms
    UNSUPPORTED lets through."""
    names = path.split("/")
    for alternative in braces(pattern):
        parts = re.split(r"/+", alternative)  # minimatch coalesces repeated slashes
        target = names[-1:] if len(parts) == 1 else names
        if len(parts) == len(target) and all(segment(p, n) for p, n in zip(parts, target)):
            return True
    return False


def braces(pattern):
    """Bash-style brace expansion: `a{b,c}d` gives abd and acd; a brace without a comma
    stays as it is."""
    depth, start, i = 0, None, 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}" and depth:
            depth -= 1
            if depth == 0:
                options = top_level_split(pattern[start + 1:i])
                if len(options) > 1:
                    head, tail = pattern[:start], pattern[i + 1:]
                    return [found for option in options for found in braces(head + option + tail)]
        i += 1
    return [pattern]


def top_level_split(text):
    parts, depth, current, i = [], 0, [], 0
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text):
            current.append(text[i:i + 2])
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(c)
        i += 1
    parts.append("".join(current))
    return parts


def segment(pattern, name):
    """One folder or file name against one segment of a glob."""
    if pattern[:1] in ("*", "?", "[") and name.startswith("."):
        return False
    return re.fullmatch(translate(pattern), name) is not None


def translate(pattern):
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            out.append(re.escape(pattern[i + 1]))
            i += 2
        elif c == "*":
            while i < len(pattern) and pattern[i] == "*":
                i += 1
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[" and class_end(pattern, i) is not None:
            end = class_end(pattern, i)
            out.append(char_class(pattern[i + 1:end]))
            i = end + 1
        else:
            out.append(re.escape(c))
            i += 1
    return "".join(out)


def class_end(pattern, start):
    """The index of the `]` closing the class opened at `start`, or None."""
    i = start + 1
    if pattern[i:i + 1] in ("!", "^"):
        i += 1
    if pattern[i:i + 1] == "]":
        i += 1
    while i < len(pattern):
        if pattern[i] == "\\":
            i += 2
            continue
        if pattern[i] == "]":
            return i
        i += 1
    return None


def char_class(body):
    negate = body[:1] in ("!", "^")
    if negate:
        body = body[1:]
    chars, i = [], 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            c = body[i + 1]
            i += 1
        chars.append(c if c == "-" else re.escape(c))
        i += 1
    return "[%s%s]" % ("^" if negate else "", "".join(chars))
