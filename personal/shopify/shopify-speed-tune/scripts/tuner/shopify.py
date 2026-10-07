"""The Shopify CLI, called the one way that cannot hit the wrong store or theme.

Every call names the store explicitly: without `--store` the CLI falls back to
the last store any theme command used on this machine, which may be another
client's. Every call runs outside the repo, so no `shopify.theme.toml`
environment adds flags, and with `SHOPIFY_FLAG_*` stripped from its environment.
Themes are named by numeric id only: push, pull and delete also match names
and wildcards. `duplicate` exits 0 when it fails, so its JSON decides.
"""

import json
import tempfile

from tuner.output import Failed
from tuner.proc import child_env, run


def _cli(store, *args, timeout=180):
    proc = run(["shopify", "theme", *args, "--store", store],
               cwd=tempfile.gettempdir(), env=child_env(CI="1"), timeout=timeout)
    if "Authorization is required" in proc.stdout + proc.stderr:
        raise Failed("shopify-login", "the Shopify CLI is not logged in to %s" % store,
                     "Ask the developer to run `shopify auth login --store %s`." % store)
    return proc


def themes(store):
    proc = _cli(store, "list", "--json")
    if proc.returncode != 0:
        raise Failed("shopify-cli", "`shopify theme list` failed: %s" % proc.stderr.strip()[-300:])
    try:
        return json.loads(proc.stdout)
    except ValueError:
        raise Failed("shopify-cli", "`shopify theme list --json` printed no JSON")


def theme(store, theme_id):
    """The theme with this id, or None when the store has no such theme."""
    proc = _cli(store, "list", "--json", "--id", str(theme_id))
    if proc.returncode != 0:
        return None
    try:
        found = json.loads(proc.stdout)
    except ValueError:
        raise Failed("shopify-cli", "`shopify theme list --id` printed no JSON")
    return next((t for t in found if str(t.get("id")) == str(theme_id)), None)


def duplicate(store, source_id, name):
    proc = _cli(store, "duplicate", "--theme", str(source_id), "--name", name,
                "--force", "--json", timeout=600)
    try:
        result = json.loads(proc.stdout)
    except ValueError:
        result = {}
    new = result.get("theme") or {}
    if proc.returncode == 0 and new.get("id") and new.get("role") == "unpublished" \
            and not result.get("errors"):
        return {"id": int(new["id"]), "name": new.get("name") or name}
    message = result.get("message") or proc.stderr.strip()[-300:] or "no JSON"
    errors = result.get("errors") or []
    detail = "; ".join(str(e) for e in errors)
    raise Failed("duplicate-failed", "duplicating theme %s failed: %s%s"
                 % (source_id, message.strip(), " (%s)" % detail if detail else ""))


def delete(store, theme_id):
    proc = _cli(store, "delete", "--theme", str(theme_id), "--force")
    if proc.returncode != 0:
        raise Failed("delete-failed", "deleting theme %s failed: %s"
                     % (theme_id, (proc.stderr or proc.stdout).strip()[-300:]))
