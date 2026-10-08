"""The guarded write: the only way the program changes a theme on the store.

It pushes files to one of the invocation's own two themes, the Working theme or
the Control theme, named by role or by id, and at the end it deletes one of
them. Before every push and every delete the program reads the theme library
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


def resolve(inv, target):
    """(role, theme) for `working`, `control` or one of their ids; refuse anything else."""
    themes = inv.data.get("themes", {})
    ours = ", ".join("%s %s" % (role, t["id"]) for role, t in sorted(themes.items()))
    role = None
    if target in themes:
        role = target
    elif str(target).isdigit():
        role = next((r for r, t in themes.items() if int(t["id"]) == int(target)), None)
    if role is None:
        raise Refused("not-invocation-theme", "%s is not one of this invocation's two themes (%s)"
                      % (target, ours),
                      "The program writes only to the Working theme and the Control theme it "
                      "created.")
    theme = themes[role]
    if theme.get("deleted"):
        raise Refused("theme-deleted", "the %s theme %s was deleted" % (role, theme["id"]))
    return role, theme


def look_up(inv, theme):
    """(the store's theme library now, the theme's entry in it or None)."""
    data = inv.data
    theme_id = int(theme["id"])
    if theme_id == int(data["store"]["published_theme"]["id"]):
        raise Refused("theme-published", "theme %s was the published theme when the invocation "
                      "started" % theme_id)
    library = shopify.themes(data["store"]["myshopify"])
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
                      % (role, theme["id"], inv.data["store"]["myshopify"]),
                      "Ask the developer what happened to it.")
    check_listed(role, theme, library, found)


def guard(inv, target, paths):
    """(role, theme) once every check before a push holds; a refusal otherwise."""
    role, theme = resolve(inv, target)
    data = inv.data
    root = data["repo"]["root"]
    for path in paths:
        if GLOB.search(path):
            raise Refused("odd-path", "%s holds a glob character, so a push would also touch "
                          "every file it matches" % path)
    shopifyignore.check(root, paths)
    repo.require_theme(root)
    configured = repo.configured_store(root)
    if configured != data["store"]["myshopify"]:
        raise Refused("store-mismatch", "this repo's shopify.theme.toml now names %s, not %s"
                      % (configured, data["store"]["myshopify"]))
    check_target(inv, role, theme)
    return role, theme


def send(inv, theme, paths):
    """The push itself, to a theme `guard` just passed: a shopify.Pushed."""
    return shopify.push(inv.data["store"]["myshopify"], theme["id"], inv.data["repo"]["root"], paths)


def push(inv, target, paths):
    """Push `paths` from the repo to the invocation's `target` theme; (role, theme, Pushed)."""
    role, theme = guard(inv, target, paths)
    return role, theme, send(inv, theme, paths)


def delete(inv, role):
    """Delete the invocation's `role` theme once the checks a push passes hold: True when this
    call deleted it, False when the theme library no longer lists it."""
    role, theme = resolve(inv, role)
    library, found = look_up(inv, theme)
    if found is None:
        return False
    check_listed(role, theme, library, found)
    shopify.delete(inv.data["store"]["myshopify"], theme["id"])
    return True
