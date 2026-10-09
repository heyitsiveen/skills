# A Sample reaches an unpublished theme through the browser's cookie jar, on the page URL plus `?pb=0`

`shopify-speed-tune` takes every Sample on one of the two unpublished themes it creates (ADR 0010). Its spec said how: such a Sample carries "the theme's preview cookie on the plain page URL, never the preview query parameter", because in the `/goal` sessions this skill replaces, the `preview_theme_id` redirect added 800–910 ms to every load. The first build gave the cookie to Lighthouse through `--extra-headers`, and both halves of that rule then failed:

- **`--extra-headers` sent the cookie to the wrong hosts, and stopped sending it to the right one.** Lighthouse adds the header to every request the page makes, so the store's preview cookie went to every third-party host on the page. And once the page set any cookie of its own, as Shopify's preview pages do, Chrome stopped sending it on later requests to the store itself.
- **The plain page URL loads the preview bar.** With the cookie alone, the store renders the theme and adds Shopify's preview bar, about 183 KB of JavaScript, to every load. Both Samples of a pair carried it, but every figure that stands alone came out low: the report's before-and-after medians, the Ceiling, and the PageSpeed comparison, which holds a baseline median against the published theme's mobile Performance score from PageSpeed Insights. On one store the accessibility score was 91 on an unpublished copy with the bar, against 94 on the published theme. Shopify's own guide to testing a theme's performance says: "Append `pb=0` (preview bar off) to each URL to prevent the preview bar from displaying during the audit, which could skew results."

So the program starts its own Chrome for Testing for each Sample, puts the theme's preview cookie in that Chrome's cookie jar for the store's host alone, and points Lighthouse at it with `--port`. Lighthouse itself is given no cookie. The page loads from its own URL plus `?pb=0`, which the developer chose on 2026-10-08. The rest of the rule stands: the program asks the store for the cookie with `preview_theme_id`, but no Sample's URL carries it; a report whose page was redirected is rejected; and the program still checks that the intended theme served the page, before the first Sample and in every report.

## Considered options

- **The cookie in `--extra-headers`, on the plain page URL.** How the first build implemented the spec. It leaks the cookie to third parties, loses it partway through the load, and loads the preview bar.
- **The cookie jar, on the plain page URL.** The spec's letter, with the cookie fixed. A pair stays fair, since both of its themes carry the bar, but every absolute figure the plan stop and the report show still comes out low.
- **`preview_theme_id` on every Sample's URL.** How Shopify's own Lighthouse CI action loads pages. Every load then pays the redirect, and Shopify says the parameter "is meant for internal previewing only".

## Consequences

Each Sample gets a Chrome the program starts and stops itself, and a small Node helper on puppeteer-core writes the cookie into its jar. Both live in the invocation's temp workspace, which `start` fills and `finish` deletes, and the smoke checker reaches the two themes the same way. The cookie reaches the helper on stdin, never on a command line, and no stored Sample holds it.

`?pb=0` removes one difference between an unpublished theme and the published one, not every difference: Shopify does not stream the HTML of a theme it serves for preview, for one. The PageSpeed comparison's warning, above a 10-point gap, stays for what remains.
