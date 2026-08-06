# Environment mismatch — dev preview disagrees with the live site

Applies when the dev preview and the published theme disagree on anything that changes how the widget renders — e.g. the product shows sold out on `shopify theme dev` but in stock on the published theme. Every measurement against a wrong-state widget is invalid, so resolve this before any inspection or capture.

The protocol runs in the MAIN conversation (steps 6 and 8 need the user); diagnostic sub-reads may be delegated. Work the steps in order, stop at the first one that fixes the mismatch, and note the step number for the final output.

**Precondition — establish theme identity.** Every step below compares two themes, so name them first. A URL records the page, never the theme: the live site and a draft preview produce byte-identical URLs. Signals: `?preview_theme_id=` in the URL; a `*.shopifypreview.com` host; and the expiries — a shareable visitor preview dies after ~2 days, a merchant preview after ~30, so an older link may silently be serving live. Undeterminable → ask the user; never assume.

1. **Rule out cache** — hard-refresh; incognito / DevTools with cache disabled; compare live vs dev in the same browser, same machine, same moment. (The Browser pane uses a clean profile separate from the personal browser — a useful cross-check against personal-browser cache/cookies.)

2. **Rule out theme-code and app-embed differences** — diff how the repo theme vs the live theme computes availability (`variant.available`, `product.available`, `inventory_quantity` logic, preorder/selling-plan handling), and compare app-embed activation between the two themes' `settings_data.json` — app embeds are per-theme, so an inventory/preorder app enabled on live but not on the dev theme can flip the sold-out state. Match the dev theme's embeds to live.

3. **Rule out market/geo/IP context** — set the SAME country via the storefront country selector on both live and dev, then re-compare. If the theme has no selector, compare live from the current IP vs a VPN in the store's primary market — if live from the current IP also shows the dev state, the cause is Markets/inventory configuration, not a dev-tool bug. Check `shopify theme dev --help` on the installed CLI version for market/country context flags, and update the CLI if outdated.

4. **Verify the data in admin** (or ask the merchant) — inventory per location; "continue selling when out of stock"; whether the product is included in the market being browsed (Markets catalogs); whether any stocked location ships to that country; sales-channel availability.

5. **Bypass the localhost proxy** — inspect via a draft theme's real-domain preview link instead of `127.0.0.1:9292`: normal geolocation, cookies, and session handling, with the live theme untouched. Get the theme to the store by whatever path this project already uses — never introduce a new deploy path to satisfy this step; if there is no established one, ask. (In the Browser pane the preview link is an external site — expect the one-time permission card.)

6. **Sidestep** (confirm with the user first) — if the widget renders identically on another in-stock product, inspect and verify on that product instead.

7. **Research the exact symptom** — Shopify docs via the Shopify dev MCP, Shopify community forums, and Shopify/cli GitHub issues for known `theme dev` availability/market-context bugs in the installed CLI version.

8. **LAST RESORT: live publish swap** — requires the user's explicit go-ahead **per occurrence**, never covered by any earlier plan approval, because it changes what customers see. **Batch it:** one swap serves every measurement that needs a live-published render — never one swap per check, because the length of the window is the entire risk. Record the current live theme's name and ID; publish the theme carrying the changes; take **captures only** inside the window — no edits, no iteration, no diagnosis, all of which belong before the swap; then re-publish the original theme — re-publishing the previous live theme IS how the draft is "unpublished". Verify afterward that the original theme is live again. Anything unexpected inside the window → re-publish the original at once and report; never debug while swapped. Prefer a low-traffic window, keep it as short as possible, and record its start and end timestamps for the final output.
