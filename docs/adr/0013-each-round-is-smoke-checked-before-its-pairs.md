# Each Round is smoke-checked before its pairs, and a smoke regression or new error removes it unmeasured

The spec for `shopify-speed-tune` ordered each Round Apply, Measure, Smoke check, Verdict. Measure is five interleaved pairs on each of the three pages, each pair a Control theme Sample then a Working theme Sample: about 30 Samples, 15–20 minutes. The verdict keeps the change only when five conditions hold, and the smoke check decides two of them: every check that passes on the Control theme also passes on the Working theme, and no console or Liquid error appears on the Working theme that is absent on the Control theme.

That order had two costs:

- **The first pair met a cold CDN.** The first Working theme Sample after a push was the first load of the changed files, so it met a cold CDN for them that its Control theme partner did not.
- **A broken change paid for its pairs anyway.** A change the smoke check failed was removed whatever its pairs said, after 15–20 minutes of them.

So each Round now goes Apply, Smoke check, Measure, Verdict, as decided on 2026-10-08. The smoke check loads every page on both themes before the first pair, which warms the store's cache with the changed files. `pairs` refuses until the open Round's smoke check is recorded, and refuses after a failed one. A Round whose smoke check finds a regression (a check that passes on the Control theme and fails on the Working theme) or a new console or Liquid error is removed at `verdict` without pairs, on `smoke-regression` or `new-error`. The detail log shows that Round's pairs as "not measured", and the report's part for the team says it was removed without being measured.

## Considered options

- **The spec's order: pairs first, then the smoke check.** Every Round pays for its pairs, a broken one included, and its first pair meets a cold CDN.

## Consequences

Every Round is smoke-checked in either order, so checking first adds no time: it only spares a broken change its pairs.

A change is final once its smoke check has run. `push` will not replace it, because the pairs would then measure a change the smoke check never saw, and a Round whose files change anyway is removed at `verdict`.

A Round removed unmeasured leaves no pairs: the report cannot say what the broken change would have gained. A developer who wants to know fixes the break and plans the change again.

The spec's reason for pairs, that store and network conditions hit both themes equally, later moved the preview cookie fetches as well. `pairs` now gets both themes' preview cookies before each pair's first Sample, so a back-off the store forces with HTTP 429 comes before a pair and never splits one.
