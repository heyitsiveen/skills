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


class Pushed:
    """What a push did: `ok`, or `errors` ({path: [message]}, possibly empty when the
    CLI gave only its warning), or `failure` when the CLI said nothing usable."""

    def __init__(self, ok=False, errors=None, warning=None, failure=None):
        self.ok = ok
        self.errors = errors or {}
        self.warning = warning
        self.failure = failure


def _json_line(text):
    text = text.strip()
    for candidate in [text] + [l for l in reversed(text.splitlines()) if l.startswith("{")]:
        try:
            found = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(found, dict):
            return found
    return None


def push(store, theme_id, root, paths):
    """Push exactly `paths` from the theme repo at `root` to theme `theme_id`.

    Each path goes in its own `--only=`, so the CLI uploads it when the local file
    differs and deletes it from the theme when the file is gone locally, and
    touches nothing else (CLI 4.8.2: both sets pass the same --only filter). The
    merchant's settings file is ignored as a second guard. The CLI exits 0 even
    when files fail, so its JSON decides: success is the expected theme, still
    unpublished, with neither `warning` nor `errors`.
    """
    proc = _cli(store, "push", "--theme", str(theme_id), "--path", root, "--json",
                "--ignore=config/settings_data.json", *["--only=" + p for p in paths], timeout=600)
    result = _json_line(proc.stdout)
    theme = (result or {}).get("theme") if isinstance((result or {}).get("theme"), dict) else None
    if proc.returncode != 0 or theme is None:
        detail = (proc.stderr or proc.stdout).strip()
        return Pushed(failure=detail.splitlines()[-1][:300] if detail else "no JSON")
    if str(theme.get("id")) != str(theme_id) or theme.get("role") != "unpublished":
        raise Failed("push-wrong-theme", "the CLI reports a push to theme %s (role %s), not to "
                     "the unpublished theme %s" % (theme.get("id"), theme.get("role"), theme_id),
                     "Stop the Rounds and show the developer this line: that theme may have "
                     "changed.")
    if theme.get("warning") or theme.get("errors"):
        errors = theme.get("errors") if isinstance(theme.get("errors"), dict) else {}
        return Pushed(errors=errors, warning=theme.get("warning") or "pushed with errors")
    return Pushed(ok=True)
