"""How this store goes live and how it goes back, read from the repo and the theme library.

Shopify's GitHub integration commits the merchant's admin edits back to the
connected branch as `shopify[bot]`, titled `Update from Shopify for theme
<name>`, where <name> is the connected theme's, `<repo>/<branch>` until someone
renames it. There is no CLI or API field for the connection, so those commits
are the evidence:

- GitHub-connected: such commits name the published theme, so whatever reaches
  that branch goes live.
- CLI-managed: no such commit, no CI workflow that deploys themes, and a
  published theme not named the way the integration names one. Only publishing
  a theme changes what customers see.
- Anything else is not recognised. The report names what was found and gives
  no steps, since a wrong step on a live store costs more than none.
"""

import fnmatch
import os
import re

from tuner import repo, shopify
from tuner.output import Stop
from tuner.text import theme_name, when

GITHUB = "github-connected"
CLI = "cli-managed"
UNKNOWN = "not-recognised"

SUBJECT = re.compile(r"Update from Shopify for theme (\S.*)$")
# A step in a CI file that pushes, publishes or deploys a theme: the Shopify CLI's
# `shopify theme push|publish`, or Theme Kit's `theme deploy`.
DEPLOY = re.compile(r"\btheme\s+(?:push|publish|deploy)\b")
CI_FILES = (".github/workflows/*.yml", ".github/workflows/*.yaml", ".gitlab-ci.yml",
            "bitbucket-pipelines.yml", ".circleci/config.yml")


class Setup:
    def __init__(self, kind, evidence, branch=None):
        self.kind = kind
        self.evidence = evidence
        self.branch = branch


def deploy_files(root):
    """The repo's CI files that deploy a theme, as repo paths."""
    found = []
    for pattern in CI_FILES:
        folder, name = os.path.split(pattern)
        try:
            names = sorted(os.listdir(os.path.join(root, folder)))
        except OSError:
            continue
        for candidate in fnmatch.filter(names, name):
            try:
                with open(os.path.join(root, folder, candidate), encoding="utf-8") as f:
                    text = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            if DEPLOY.search(text):
                found.append(os.path.join(folder, candidate))
    return found


def connected_themes(root):
    """{theme name: (commits, latest date)} from the GitHub integration's commits on any ref."""
    log = repo.git(root, "log", "--all", "--fixed-strings", "--author=shopify[bot]",
                   "--format=%cI%x09%s").stdout
    found = {}
    for line in log.splitlines():
        stamp, _, subject = line.partition("\t")
        match = SUBJECT.match(subject.strip())
        if match:
            name = match.group(1).strip()
            count, latest = found.get(name, (0, ""))
            found[name] = (count + 1, max(latest, stamp[:10]))
    return found


def branch_named_by(root, name):
    """The branch a theme named `<repo>/<branch>` would be connected to, when the repo has it."""
    match = re.fullmatch(r"[^/\s]+/(\S+)", name or "")
    if not match:
        return None
    refs = repo.git(root, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes")
    branch = match.group(1)
    for ref in refs.stdout.split():
        if ref == "refs/heads/" + branch or re.fullmatch(r"refs/remotes/[^/]+/" + re.escape(branch),
                                                         ref):
            return branch
    return None


def detect(root, live_name):
    deploys = deploy_files(root)
    themes = connected_themes(root)
    evidence = []
    if deploys:
        evidence.append("a CI workflow that deploys themes: %s"
                        % ", ".join("`%s`" % path for path in deploys))
    if themes:
        evidence.append("commits from Shopify's GitHub integration for %s" % ", ".join(
            "`%s` (%d, the latest on %s)" % (name, count, latest)
            for name, (count, latest) in sorted(themes.items())))
    if deploys:
        return Setup(UNKNOWN, evidence)
    if themes:
        if live_name in themes and "/" in live_name:
            return Setup(GITHUB, evidence, branch=live_name.split("/", 1)[1])
        evidence.append("the published theme is named `%s`, %s" % (
            live_name, "which does not say the branch it is connected to" if live_name in themes
            else "which none of those commits names"))
        return Setup(UNKNOWN, evidence)
    branch = branch_named_by(root, live_name)
    if branch:
        evidence.append("no commit from Shopify's GitHub integration, yet the published theme is "
                        "named `%s`, the way Shopify's GitHub integration names the theme it "
                        "connects to a branch, and this repo has the branch `%s`"
                        % (live_name, branch))
        return Setup(UNKNOWN, evidence)
    return Setup(CLI, ["no commit from Shopify's GitHub integration, and no CI workflow that "
                       "deploys themes"])


def live_theme(inv):
    """(theme, note): the store's published theme now, read from the theme library, or the one
    recorded at the start, with the reason, when the library cannot be read."""
    recorded = inv.data["store"]["published_theme"]
    try:
        library = shopify.themes(inv.data["store"]["myshopify"])
    except Stop as failure:
        return recorded, "the theme library could not be read (%s), so the published theme " \
                         "recorded at the start stands in for it" % failure.message
    live = [t for t in library if t.get("role") == "live"]
    if len(live) != 1:
        return recorded, "the theme library lists %d published themes, so the one recorded at " \
                         "the start stands in" % len(live)
    return {"id": int(live[0]["id"]), "name": live[0].get("name")}, None


def changed(inv, live):
    """True when another theme than the one copied at the start, and than the Working theme,
    is published now."""
    data = inv.data
    working = data["themes"].get("working") or {}
    return int(live["id"]) not in (int(data["store"]["published_theme"]["id"]),
                                   int(working.get("id") or 0))


HEADLINES = {
    GITHUB: "**This store is GitHub-connected.** Shopify's GitHub integration commits the "
            "merchant's edits to this repo for the theme `%(live)s`, which is the published "
            "theme, so whatever reaches the branch `%(branch)s` goes live.",
    CLI: "**This store is CLI-managed.** Nothing deploys from this repo: it holds no commit from "
         "Shopify's GitHub integration and no CI workflow that deploys themes, so customers see a "
         "change only once a theme is published.",
    UNKNOWN: "**This store's setup was not recognised**, so this report gives no steps for going "
             "live or going back. What was found:",
}


def section(inv, setup, live, kept):
    """The team's `Going live and going back` section, for this store's setup."""
    data = inv.data
    recorded = data["store"]["published_theme"]
    working = data["themes"].get("working") or {}
    lines = ["### Going live and going back", ""]
    if working and int(live["id"]) == int(working["id"]):
        return lines + ["**The Working theme is the published theme now**: this store went live "
                        "with it. To go back, publish %s again." % theme_name(recorded), ""]
    if changed(inv, live):
        lines += ["**The published theme changed during this invocation.** It was %s when the "
                  "Working theme was copied from it, and it is %s now. The Working theme holds "
                  "#%s's code and the kept changes, so settle with the merchant which theme goes "
                  "live before any step below." % (theme_name(recorded), theme_name(live),
                                                   recorded["id"]), ""]
    lines += [HEADLINES[setup.kind] % {"live": live["name"], "branch": setup.branch}, ""]
    if setup.kind == UNKNOWN:
        return lines + not_recognised(inv, setup, kept)
    if not kept:
        return lines + ["No Round was kept, so there is nothing to publish: the published theme "
                        "stays as it is. The Working theme %s is still a copy of it; delete it "
                        "once you no longer need it." % theme_name(working), ""]
    return lines + (github_steps(inv, setup) if setup.kind == GITHUB else cli_steps(inv, live))


def not_recognised(inv, setup, kept):
    data = inv.data
    where = "Every kept change is on the Working theme %s and on the branch `%s`." % (
        theme_name(data["themes"].get("working") or {}), data["repo"].get("branch")) if kept \
        else "No Round was kept, so there is nothing to publish."
    return ["- %s." % found for found in setup.evidence] + [
        "",
        "Check the published theme's card in the admin, where a theme connected to GitHub shows "
        "its repository, branch and last commit, then go live and go back the way this store "
        "always does. " + where,
        "",
    ]


def github_steps(inv, setup):
    data = inv.data
    connected = setup.branch
    return [
        "To go live:", "",
        "1. Merge the branch `%s` into `%s` and push `%s`. Shopify updates the published theme "
        "from it within seconds; the theme card's **View logs** lists any file it could not sync. "
        "The merchant's own edits reach `%s` as Shopify's commits, so a merge conflict can only "
        "be in a file a kept Round changed, template JSON first."
        % (data["repo"]["branch"], connected, connected, connected),
        "2. Leave the Working theme %s unpublished: it is not connected to GitHub, so publishing "
        "it would take the store off its GitHub workflow. Delete it once the store checks out."
        % theme_name(data["themes"]["working"]),
        "",
        "To go back, revert the merge on `%s` (`git revert -m 1 <merge commit>`) and push `%s`: "
        "Shopify syncs the published theme back. The admin's **Reset to last commit** only "
        "re-syncs the theme to the branch's latest commit, so it is not a way back."
        % (connected, connected),
        "",
    ]


def cli_steps(inv, live):
    data = inv.data
    store, working = data["store"]["myshopify"], data["themes"]["working"]
    return [
        "To go live:", "",
        "1. Bring over what the merchant changed on the published theme %s since the Working "
        "theme was copied from it, on %s: compare its `config/settings_data.json`, "
        "`templates/*.json` and `sections/*.json` with the Working theme's. Pull each theme's "
        "copies into a temporary folder to compare them, never into this repo: `shopify theme "
        "pull --theme <id> --only <file> --path <folder> --store %s`."
        % (theme_name(live), when(data.get("created_at")), store),
        "2. Publish the Working theme %s: in the admin, **Online Store → Themes**, its **…** "
        "menu, **Publish**; or `shopify theme publish --theme %s --store %s`."
        % (theme_name(working), working["id"], store),
        "3. Merge the branch `%s` into `%s`, so the repo holds what is live."
        % (data["repo"]["branch"], data["repo"]["start_branch"]),
        "",
        "To go back, publish %s again: publishing the Working theme leaves it in the theme "
        "library, unpublished and unchanged." % theme_name(live),
        "",
    ]
