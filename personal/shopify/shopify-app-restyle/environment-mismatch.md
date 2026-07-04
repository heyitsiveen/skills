# Environment-mismatch protocol

Fires when the app widget renders in a **different state** on `shopify theme dev`
than on the published/live store — the classic case: a product is sold out on dev
but in stock on live (or the reverse), and the widget renders differently per state.

A comparison against the **wrong state** is not evidence. Never inspect or verify
until dev and live agree on the state the Figma frames depict.

Diagnose in order; **stop at the first step that resolves it.** Cheap and local
first, customer-facing last. Note which step fixed it — it goes in the final output.

1. **Cache.** Hard-refresh; incognito, or DevTools with cache disabled. Compare live
   vs dev in the same browser, same machine, same moment.

2. **Theme code + app embeds.** Diff how the dev/repo theme vs the live theme computes
   availability (`variant.available`, `product.available`, `inventory_quantity`,
   preorder / selling-plan handling). Then compare app-embed activation in each
   theme's `settings_data.json` — app embeds are **per-theme**, so an inventory or
   preorder app enabled on live but not on dev will flip the state. Match the dev
   theme's embeds to live.

3. **Market / geo / IP.** Set the **same country** via the storefront country selector
   on both live and dev, then re-compare. No selector? Compare live from the current
   IP vs a VPN in the store's primary market — if live from the current IP *also*
   shows the wrong state, the cause is Markets/inventory config, not a dev-tool bug.
   Check `shopify theme dev --help` on the installed CLI for market/country flags;
   update the CLI if outdated.

4. **Data (admin / merchant).** Verify: inventory per location; "continue selling when
   out of stock"; whether the product is in the browsed market's catalog (Markets);
   whether any stocked location ships to that country; sales-channel availability. Ask
   the merchant if you can't reach admin.

5. **Bypass the localhost proxy.** `shopify theme push --unpublished`, then inspect via
   that theme's real-domain preview link — real geolocation, cookies, and session, with
   the live theme untouched.

6. **Sidestep.** If the widget renders identically on another in-stock product, inspect
   and verify on that product instead — **confirm with the user first.**

7. **Research the exact symptom.** Shopify docs via the Shopify dev MCP; Shopify
   community forums; `Shopify/cli` GitHub issues for known `theme dev`
   availability/market-context bugs in the installed CLI version.

8. **LAST RESORT — live publish swap.** Requires the user's **explicit go-ahead** (the
   workflow is otherwise gate-free, but this changes what customers see). Record the
   current live theme's name and ID → publish the repo/draft theme → perform the
   inspection/captures **immediately** → re-publish the original theme (re-publishing
   the previous live theme is how the draft becomes "unpublished" again). Afterward,
   **verify the original theme is live again.** Prefer a low-traffic window; keep the
   swap as short as possible.
