"""The invocation's ledger: everything the program knows, in one JSON file.

It lives at `<repo>/.agent/shopify-speed-tune/<invocation>/ledger.json`, beside
the Sample reports and the report it produces. The ledger is the single source
of truth: a Measurement is computed from its Samples on demand, never stored.

The interface is small on purpose:

    inv = ledger.current("sample")     # the open invocation of this repo
    inv.data["samples"].append({...})  # each concern owns its own top-level key
    inv.log("sample", "s0003 recorded")
    inv.save()

Every write replaces the file atomically, so a crash leaves the last good copy.
"""

import json
import os

from tuner import clock, lock, repo
from tuner.output import Refused

AGENT_DIR = os.path.join(".agent", "shopify-speed-tune")
SCHEMA = 1


class Invocation:
    def __init__(self, folder, data):
        self.folder = folder
        self.data = data

    @property
    def id(self):
        return self.data["invocation"]

    @property
    def path(self):
        return os.path.join(self.folder, "ledger.json")

    def file(self, *parts):
        return os.path.join(self.folder, *parts)

    def page_url(self, page):
        path = self.data.get("pages", {}).get(page)
        if not path:
            raise Refused("no-page", "the %s page is not set" % page,
                          "Run `pages` to propose it, or `pages --%s <path>` to set it." % page)
        return self.data["store"]["url"].rstrip("/") + path

    def log(self, op, text):
        self.data.setdefault("events", []).append({"at": clock.now(), "op": op, "text": text})

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, self.path)


def folder_for(repo_root, invocation_id):
    return os.path.join(repo_root, AGENT_DIR, invocation_id)


def create(repo_root, invocation_id, data):
    folder = folder_for(repo_root, invocation_id)
    os.makedirs(folder)
    data = dict(data, schema=SCHEMA, invocation=invocation_id, created_at=clock.now(), events=[])
    inv = Invocation(folder, data)
    inv.save()
    return inv


def load(folder):
    with open(os.path.join(folder, "ledger.json"), encoding="utf-8") as f:
        return Invocation(folder, json.load(f))


def current(op):
    """The unfinished invocation, which must belong to the repo the program runs in."""
    held = lock.read()
    if held is None:
        raise Refused("no-invocation", "no invocation is open on this machine",
                      "Open one with `start`.")
    here = repo.root()
    if os.path.realpath(held.get("repo", "")) != here:
        raise Refused("other-repo", "the open invocation belongs to %s, not %s (%s)"
                      % (held.get("repo"), here, lock.describe(held)),
                      "Run the program from that repo, or finish that invocation first.")
    try:
        inv = load(os.path.dirname(held.get("ledger", "")))
    except (OSError, ValueError):
        raise Refused("no-ledger", "the lock names a ledger that cannot be read: %s"
                      % held.get("ledger"),
                      "If that invocation was abandoned, clear the lock with "
                      "`unlock --invocation %s`." % held.get("invocation"))
    lock.touch(inv.id, op)
    return inv


def find(invocation_id=None):
    """The open invocation, or a named one of this repo (finished ones included)."""
    if invocation_id is None:
        return current("status")
    folder = folder_for(repo.root(), invocation_id)
    if not os.path.isfile(os.path.join(folder, "ledger.json")):
        raise Refused("no-invocation", "this repo has no invocation %s" % invocation_id)
    return load(folder)
