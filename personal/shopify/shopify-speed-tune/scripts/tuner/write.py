"""The guarded write: the only way the program changes a theme on the store.

It pushes files to one of the invocation's own two themes, the Working theme or
the Control theme, named by role, and at the end it deletes one of them.
Before every push and every delete the program reads the theme library
back from the store and refuses unless that theme is still unpublished and no
other theme is named like its id: the CLI matches `--theme` by name too, a
push taking the first match, live theme first, and a delete every match. A
push also refuses a repo whose `shopify.theme.toml` no longer names the
invocation's store, any path holding a glob character, since the CLI deletes
whatever its `--only` filter matches and the file lacks, and any path the
repo's `.shopifyignore` excludes, since the CLI skips it without a word.
"""

import re

from tuner import repo, shopify, shopifyignore
from tuner.output import Refused

GLOB = re.compile(r"[*?\[\]{}()!\\]")


def resolve(inv, role):
    """The invocation's `role` theme, working or control; a refusal once it was deleted."""
    theme = inv.data["themes"][role]
    if theme.get("deleted"):
        raise Refused("theme-deleted", "the %s theme %s was deleted" % (role, theme["id"]))
    return theme


def look_up(inv, theme):
    """(the store's theme library now, the theme's entry in it or None)."""
    theme_id = int(theme["id"])
    if theme_id == int(inv.data["store"]["published_theme"]["id"]):
        raise Refused("theme-published", "theme %s was the published theme when the invocation "
                      "started" % theme_id)
    library = shopify.themes(inv.myshopify)
    return library, next((t for t in library if int(t["id"]) == theme_id), None)


def check_listed(role, theme, library, found):
    """Refuse unless the library lists the theme as unpublished and names no other theme like
    its id."""
    theme_id = int(theme["id"])
    if found.get("role") == "live":
        raise Refused("theme-published", "the %s theme %s is now the published theme"
                      % (role, theme_id),
                      "Customers see it now; ask the developer before anything else is written.")
    if found.get("role") != "unpublished":
        raise Refused("theme-not-unpublished", "the %s theme %s is now a %s theme"
                      % (role, theme_id, found.get("role")))
    clash = [t for t in library if int(t["id"]) != theme_id
             and str(t.get("name", "")).strip().lower() == str(theme_id)]
    if clash:
        raise Refused("theme-name-clash", "theme %s is named %s, the id of the %s theme, and the "
                      "CLI matches names too" % (clash[0]["id"], theme_id, role))


def check_target(inv, role, theme):
    """Refuse unless the store still lists the theme as an unpublished theme of its own name."""
    library, found = look_up(inv, theme)
    if found is None:
        raise Refused("theme-missing", "the %s theme %s is no longer in %s's theme library"
                      % (role, theme["id"], inv.myshopify),
                      "Ask the developer what happened to it.")
    check_listed(role, theme, library, found)


def guard(inv, role, paths):
    """The `role` theme once every check before a push to it holds; a refusal otherwise."""
    theme = resolve(inv, role)
    root = inv.root
    for path in paths:
        if GLOB.search(path):
            raise Refused("odd-path", "%s holds a glob character, so a push would also touch "
                          "every file it matches" % path)
    shopifyignore.check(root, paths)
    repo.require_theme(root)
    configured = repo.configured_store(root)
    if configured != inv.myshopify:
        raise Refused("store-mismatch", "this repo's shopify.theme.toml now names %s, not %s"
                      % (configured, inv.myshopify))
    check_target(inv, role, theme)
    return theme


def send(inv, theme, paths):
    """The push itself, to a theme `guard` just passed: a shopify.Pushed."""
    return shopify.push(inv.myshopify, theme["id"], inv.root, paths)


def push(inv, role, paths):
    """Push `paths` from the repo to the invocation's `role` theme; (theme, Pushed)."""
    theme = guard(inv, role, paths)
    return theme, send(inv, theme, paths)


def delete(inv, role):
    """Delete the invocation's `role` theme once the checks a push passes hold: True when this
    call deleted it, False when the theme library no longer lists it."""
    theme = resolve(inv, role)
    library, found = look_up(inv, theme)
    if found is None:
        return False
    check_listed(role, theme, library, found)
    shopify.delete(inv.myshopify, theme["id"])
    return True
