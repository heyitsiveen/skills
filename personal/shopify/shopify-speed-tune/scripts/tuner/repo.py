"""The client theme repo the program runs in: its root, its store, its branch."""

import os
import re
import tomllib

from tuner.output import Refused
from tuner.proc import run

TOML = "shopify.theme.toml"


def root(cwd=None):
    """The repo root of the working directory, or a refusal outside a git repo."""
    proc = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd or os.getcwd())
    if proc.returncode != 0:
        raise Refused("not-a-repo", "%s is not inside a git repo" % (cwd or os.getcwd()),
                      "Run the program from the client theme repo's root.")
    return os.path.realpath(proc.stdout.strip())


def require_theme(path):
    for needed in ("layout/theme.liquid", "config/settings_schema.json"):
        if not os.path.isfile(os.path.join(path, needed)):
            raise Refused("not-a-theme", "%s has no %s, so it is not a theme's root" % (path, needed))


def myshopify(value):
    """`handle`, `handle.myshopify.com` or its URL, as `handle.myshopify.com`."""
    host = value.strip().lower()
    for prefix in ("https://", "http://"):
        if host.startswith(prefix):
            host = host[len(prefix):]
    host = host.split("/")[0]
    if "." not in host:
        host += ".myshopify.com"
    return host


def git(path, *args):
    return run(["git", *args], cwd=path)


def git_version(path):
    """(major, minor) of the git on PATH, e.g. (2, 54)."""
    found = re.search(r"(\d+)\.(\d+)", git(path, "--version").stdout)
    return (int(found.group(1)), int(found.group(2))) if found else (0, 0)


def current_branch(path):
    proc = git(path, "symbolic-ref", "--quiet", "--short", "HEAD")
    if proc.returncode != 0:
        raise Refused("detached-head", "%s has no branch checked out" % path,
                      "Check out the branch the invocation should start from.")
    return proc.stdout.strip()


def head(path):
    return git(path, "rev-parse", "HEAD").stdout.strip()


def require_clean(path):
    """Tracked files must match HEAD, so the invocation's branch starts from a known state."""
    proc = git(path, "status", "--porcelain", "--untracked-files=no")
    if proc.stdout.strip():
        raise Refused("repo-dirty", "%s has uncommitted changes to tracked files" % path,
                      "Commit or stash them first; a Round must start from a committed state.")


def branch_exists(path, name):
    return git(path, "rev-parse", "--verify", "--quiet", "refs/heads/" + name).returncode == 0


def create_branch(path, name):
    proc = git(path, "switch", "-q", "-c", name)
    if proc.returncode != 0:
        raise Refused("branch-failed", "cannot create branch %s: %s" % (name, proc.stderr.strip()))


def exclude_from_git(path, entry=".agent/"):
    """Keep the skill's folder out of git through .git/info/exclude, never .gitignore."""
    probe = os.path.join(entry, "shopify-speed-tune", "ledger.json")
    if git(path, "check-ignore", "-q", probe).returncode == 0:
        return False
    info = git(path, "rev-parse", "--git-path", "info/exclude").stdout.strip()
    info = info if os.path.isabs(info) else os.path.join(path, info)
    os.makedirs(os.path.dirname(info), exist_ok=True)
    with open(info, "a", encoding="utf-8") as f:
        f.write("\n" + entry + "\n")
    return True


def configured_store(path):
    """The store `shopify.theme.toml` names, refusing any file that says more.

    Its default environment is applied to every Shopify CLI call made from the
    repo, so a `theme`, `live` or `password` key there would steer writes
    the program never chose.
    """
    toml_path = os.path.join(path, TOML)
    if not os.path.isfile(toml_path):
        raise Refused("no-store-config", "%s has no %s naming its store" % (path, TOML),
                      "client-theme-onboarding writes one; never guess the store from the folder name.")
    try:
        with open(toml_path, "rb") as f:
            config = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise Refused("no-store-config", "%s cannot be read: %s" % (TOML, e))
    default = config.get("environments", {}).get("default")
    if not isinstance(default, dict) or not default.get("store"):
        raise Refused("no-store-config", "%s has no [environments.default] store" % TOML)
    extra = sorted(set(default) - {"store"})
    if extra:
        raise Refused("store-config-has-more",
                      "%s's [environments.default] sets %s besides store; every CLI call "
                      "would inherit it" % (TOML, ", ".join(extra)))
    return myshopify(str(default["store"]))
