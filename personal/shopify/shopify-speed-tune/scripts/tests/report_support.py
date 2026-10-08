"""Shared set-up for the report tests: invocations whose Rounds ran to their stop.

Each scenario starts from round_support's approved invocation (the real pages,
their real baselines and Ceilings, an approved plan of two items), adds the
developer's PageSpeed Insights mobile Performance scores and the baseline
desktop Measurements, runs its Rounds on pairs derived from the real reports,
and takes the final desktop Measurements. Every Sample is a real report with only its score fields, and
for the Working theme its asset folder, edited.

A scenario is built once and kept as a copy; each test gets that copy back at
the same path, as round_support does for the approved plan.

The real figures, worked by hand from the fixtures:

    mobile baseline   home 50 (36-56)  collection 61 (46-64)  product 44 (43-46)
    Ceiling           home 59 (58-65)  collection 71 (69-82)  product 65 (59-68)
    target            the Ceiling on every page: each is below the requested 80
"""

import atexit
import json
import shutil
import tempfile
from pathlib import Path

from plan_support import PAGES
from round_support import (ASSET_FOLDERS, ITEMS, NEUTRAL, WIN_4, add_to_cart_fails, apply_item,
                           approved, checked, measure, write)
from support import FAILING_HOOK, Sandbox, read_report

# The developer's PageSpeed Insights mobile Performance scores: home 11 above its baseline
# median (a warning), collection 3 below, product 3 above.
PSI = {"home": 61, "collection": 58, "product": 47}

# Desktop Performance scores of five Samples per page: the baseline on the Control
# theme, and the final Measurement on the Working theme.
DESKTOP_BEFORE = {"home": (86, 88, 88, 90, 85), "collection": (88,) * 5,
                  "product": (71, 70, 72, 71, 69)}
DESKTOP_AFTER = {"home": (90, 91, 89, 92, 90), "collection": (89,) * 5,
                 "product": (75, 74, 76, 75, 73)}

# Gains that lift every page's Working median past its target: 50 -> 60 on home,
# 61 -> 72 on collection and 44 -> 66 on product.
PAST_THE_TARGETS = {"home": (10,) * 5, "collection": (11,) * 5, "product": (22,) * 5}

# What P1 changes in the index template besides the hero snippet, in the
# scenario that keeps it.
INDEX_EAGER = json.dumps({"sections": {"hero": {"type": "hero",
                                                "settings": {"image_loading": "eager"}}},
                          "order": ["hero"]}, indent=2) + "\n"


def desktop_report(box, page, theme, score, n):
    """The page's real desktop report as `theme` served it, with its Performance score set."""
    data = read_report("%s-desktop-1" % page)
    data["categories"]["performance"]["score"] = score / 100.0
    text = json.dumps(data).replace(ASSET_FOLDERS["control"], ASSET_FOLDERS[theme])
    path = box.root / ("%s-desktop-%s-%d-%d.json" % (page, theme, n, score))
    path.write_text(text)
    return path


def run(box, *args):
    result = box.run(*args)
    box.test.assertEqual(result.code, 0, result)
    return result


def desktop(box, op, theme, scores):
    """Record one desktop Measurement per page: `sample` for the baseline, `final` at the end."""
    for page in PAGES:
        files = [desktop_report(box, page, theme, score, n)
                 for n, score in enumerate(scores[page], 1)]
        args = [op, "--page", page] + (["--device", "desktop"] if op == "sample" else [])
        run(box, *args, *sum((["--report", f] for f in files), []))


def round_of(box, item, gains, apply=None, smoke=None):
    """Open a Round for `item`, make its change and push it, smoke-check it, take its pairs
    when the check passed, and decide."""
    run(box, "round", "--item", item)
    (apply or (lambda b: apply_item(b, item)))(box)
    run(box, "push")
    if checked(box, smoke).lines("SMOKE")[-1].endswith("result pass"):
        measure(box, gains)
    return run(box, "verdict")


def eager_hero_and_index(box):
    apply_item(box, "P1")
    write(box, "templates/index.json", INDEX_EAGER)


def reached(box):
    """P2 is kept past every target, so the Rounds stop at their first verdict."""
    round_of(box, "P2", PAST_THE_TARGETS)


def missed(box):
    """P1 (with a template JSON change) is kept on four wins in five on home, P2 is
    removed for winning nowhere, and the plan is used up short of every target."""
    round_of(box, "P1", {"home": WIN_4}, apply=eager_hero_and_index)
    round_of(box, "P2", {"home": NEUTRAL})


def none_kept(box):
    """Neither item wins anywhere: both are removed and nothing is left to publish."""
    round_of(box, "P1", {"home": NEUTRAL})
    round_of(box, "P2", {"home": NEUTRAL})


def first_unmeasured(box):
    """P1's Round ends unpushed and unmeasured; P2 is then kept past every target."""
    run(box, "round", "--item", "P1")
    apply_item(box, "P1")
    run(box, "verdict", "--remove")
    round_of(box, "P2", PAST_THE_TARGETS)


def smoke_removed(box):
    """P1's smoke check finds add to cart broken, so it is removed before any pair; P2 is
    then kept past every target."""
    round_of(box, "P1", {}, smoke=add_to_cart_fails)
    round_of(box, "P2", PAST_THE_TARGETS)


# Each scenario: the `start` arguments and the repo's pre-commit hook it is approved
# with, and the Rounds it runs.
SCENARIOS = {
    "reached": ((), None, reached),
    "missed": ((), None, missed),
    "none-kept": ((), None, none_kept),
    "first-unmeasured": ((), None, first_unmeasured),
    "smoke-removed": ((), None, smoke_removed),
    "hook-passed": ((), "exit 0\n", reached),
    "hook-bypassed": (("--no-verify-approved",), FAILING_HOOK, reached),
}
FROZEN = {}


def ran(test, scenario):
    """An invocation whose Rounds ran to their stop as `scenario` says, with every
    figure the report reads recorded and no report written yet."""
    if scenario in FROZEN:
        root, frozen = FROZEN[scenario]
        return Sandbox.restored(test, root, frozen)
    start_args, pre_commit, rounds = SCENARIOS[scenario]
    box = approved(test, ITEMS, *start_args, pre_commit=pre_commit)
    run(box, "psi", *sum((["--%s" % page, str(score)] for page, score in PSI.items()), []))
    desktop(box, "sample", "control", DESKTOP_BEFORE)
    rounds(box)
    test.assertTrue(box.run("status").lines("STOP"), "the Rounds must have stopped")
    desktop(box, "final", "working", DESKTOP_AFTER)
    frozen = Path(tempfile.mkdtemp(prefix="speed-tune-frozen-"))
    shutil.copytree(box.root, frozen / "copy", symlinks=True)
    atexit.register(shutil.rmtree, frozen, True)
    FROZEN[scenario] = (box.root, frozen / "copy")
    return box
