# The speed report's format

`report` writes `.agent/shopify-speed-tune/<invocation>/report.md` from the ledger, whole, every time it runs, so the file always matches the ledger. It opens with the store, the invocation, the pinned Lighthouse and Chrome for Testing, the requested score and an **Outcome** sentence: every page reached its target, or the plan was used up, or the Rounds were ended before it, with how many pages reached their targets. Two parts follow: **For the team**, which the developer sends, and the **Detail log** behind it.

Every heading below is one of the report's own, in the report's order; a test holds the two to the same list. A section marked *only when* is left out otherwise.

## For the team

### What changed

How many plan items were kept, then each item: kept, with its Round, its commit and its pairs on every page; removed, with its Round and why, "without being measured" when its pairs did not decide it; or not tried, and why. When the kept Rounds were committed with `--no-verify`, the end of what the repo's pre-commit hook said before the invocation: its summary, the lines counting its problems, then its last line.

### Performance by page

Per page, mobile, each figure the median of five Samples with its range: **Before**, the baseline; **After**, the latest Measurement of what the Working theme holds, and the Round that took it; the **Target**; the **Ceiling**, an estimate; and the result, reached or missed by how many points. Each Ceiling note `ceiling` printed follows, then desktop at the start and at the end. A final desktop Measurement not taken reads – and is named below the table.

### PageSpeed beside the baseline

The developer's PageSpeed Insights mobile Performance scores, given at the plan stop, beside the baseline medians, and a warning for each gap of more than 10 points.

### Apps and tags

Every app and tag the baseline Samples loaded, costliest first: main-thread time, then transfer size, on each page.

### Template JSON

Each template JSON file a kept Round changed, which the merchant may also have edited: review it before going live.

### Going live and going back

The steps for this store's setup, which `REPORT setup` names: `github-connected` or `cli-managed`. For `not-recognised`, what the program found, and no steps.

### Missed targets

*Only when a page missed its target.* Per page: where its target comes from, what each Round did there, its costliest apps and tags, how the Rounds ended, and the reason and next plan recorded with `report --missed`, as [missed-targets.md](missed-targets.md) describes.

## Detail log

### Invocation

The store, the invocation, the requested score, the published theme at the start, the Working theme and the Control theme, the branch, the commit hook, the plan's approval, the PageSpeed Insights scores and the stop.

### Tools

The Lighthouse, Chrome for Testing and puppeteer-core pinned for the invocation, then the versions the Samples' own reports name.

### Plan

*Only when a plan was recorded.* Every plan item with its pages, cause and expected effect, and the Round that used it.

### Measurements

Every Measurement, each metric's median and range, and every Sample rejected before it was recorded.

### Smoke checks

*Only when a smoke check ran.* Each one, with its result, its findings and each page on both themes.

### Rounds

*Only when a Round opened.* Each Round: its item, change, pushes, pairs, smoke check and verdict, then its commit or its revert, and a table of its pairs.
