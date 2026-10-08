# Explaining a missed target

`report` writes everything else in `report.md` from the ledger. A page that missed its target also needs what only you can give: why it stayed short, and what to try next. Until you record them, `report` prints `REPORT missed <page> unexplained` for the page and its Missed targets entry reads "not written yet".

## The file

One JSON object keyed by page, holding every missed page, since recording again replaces every entry:

    {"product": {"reason": "…",
                 "next": [{"change": "…", "cause": "…", "effect": "…"}]}}

Record it with `report --missed <file>`, which writes the report again. It refuses an entry for a page that reached its target, a page with no reason or no next item, and a next item missing its change, cause or effect.

## The reason

One or two sentences on why the page stayed short, grounded in the facts the report already prints under the page:

- whether its target is its Ceiling or the requested score
- what each Round on the page did, and why a removed one was removed
- which apps and tags cost the page most

When the page sits at its Ceiling and the rest is apps and tags, say so plainly: theme work has done what it can, and the rest is the merchant's conversation.

## The next plan

One item per change worth a later invocation, largest expected effect first, each in the plan items' shape: the change, the cause it answers, the expected effect ("unmeasured" when no evidence backs it).

- Theme changes not tried yet come first. Check each against [regressions.md](regressions.md), and take a known defect's fix from [known-defects.md](known-defects.md).
- A removed item comes back only with what would change its verdict: a different form of the change, or the fix for whatever made it lose a page.
- An app or tag that costs the page is the merchant's decision: name it with its measured cost, as an item for the merchant to weigh.
