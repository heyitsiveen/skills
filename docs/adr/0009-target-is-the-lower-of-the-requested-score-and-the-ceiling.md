# A page's target is the lower of the requested score and its Ceiling

`shopify-speed-tune` replaces a free-text `/goal` prompt — "get the Lighthouse score to 80–90, stop after 5 tries" — that ran eight times across seven client stores. The fixed number was unreachable on some of those stores, and nothing in the loop could tell that early:

- One store's mobile Performance score topped out at 58–60 with every optional theme-owned request removed. Its apps and tags set the limit, and every try after the developer ruled out app changes gained 0–2 points.
- Another store reached only 79 with every tag blocked, against a target of 90.

An unreachable target is also where a coding agent starts gaming the measure instead of improving the page.

So before the first Round, the skill measures each page's Ceiling: the highest Performance score theme work alone can reach, with the store's apps and tags left as they are. The page's target is the lower of the requested score (80 by default) and that Ceiling. Each page must reach its own target, because an average across pages would let one slow page hide behind two fast ones.

## Considered options

- **A fixed score for every store.** Simple, and it is the number clients quote. But it is unreachable wherever apps cost more than the theme can win back.
- **Real-user Core Web Vitals as the target.** This is the real goal, but the data lags about 28 days and small stores have none, so it cannot judge a Round. It still reaches the team through the PageSpeed screenshot they already share.
- **Per-metric lab budgets (LCP, TBT, CLS) with no score.** These are closer to what Google ranks on, but the team and its clients speak in the Performance score.

## Consequences

A run can end with "target reached" below 80. The report gives each page's Ceiling and what holds it down, including the measured cost of each app and tag, so a low number arrives with its explanation rather than as an excuse.
