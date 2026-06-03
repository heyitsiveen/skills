---
name: shopify-app-style-override-from-figma
description: Use when the user wants to OVERRIDE the visual styles of a third-party Shopify app widget (e.g., upsell bundles, review widgets, popup app blocks, deals embeds, social-proof tiles, recommendation carousels) to match a Figma design — without modifying the app's code or HTML. Inspects the live rendered DOM via the chrome-in-chrome MCP to extract the app's element tree, class names, and computed styles, then writes CSS overrides scoped under a containing panel id for clean specificity wins — and matching the app's own !important when it uses one. Triggers on phrases like "override the styles of [App Name]", "restyle the [app] widget to match Figma", "match this Figma — the widget is from a Shopify app", "the app block looks wrong, fix the styling", "skin the bundle widget", "the upsell renders fine but it doesn't match the design", or any request providing a live preview URL + Figma URL where the styled element is injected by a Shopify app rather than authored in the theme. Does NOT modify the app, its HTML, or its embed registration — purely CSS overrides in an existing theme stylesheet. Distinct from the three "from-Figma" siblings: not composing JSON (`shopify-add-section-or-preset-from-figma`), not creating .liquid files (`shopify-build-section-or-block-from-figma`), and not editing first-party theme code (`shopify-update-existing-section-from-figma`) — exclusively for app-injected DOM.
user-invocable: true
---

# Shopify App Style Override From Figma

Restyle a Shopify app's injected widget (theme embed, app block, deals embed, etc.) to match a Figma design using CSS overrides only. No app code is modified. The override CSS lives in an existing theme stylesheet (typically the `<style>` block of the parent snippet or section that contains the widget) and beats the app's own styles via id-scoped specificity.

This skill is the **third-party-widget** counterpart to:
- `shopify-add-section-or-preset-from-figma` — composes a NEW section in JSON from existing primitives
- `shopify-build-section-or-block-from-figma` — creates a NEW `.liquid` file
- `shopify-update-existing-section-from-figma` — re-aligns existing first-party sections

Use this skill when the styled element is rendered by a Shopify app's runtime — you can't edit its HTML, only override its CSS.

## The rule

**Never modify the app's HTML, JS, or registration.** You don't own the widget. Your override surface is CSS only, scoped under an existing theme container.

**Lead with specificity; reach for `!important` only to match the app's own.** The default tool is id-scoping: `#ContainerId .app-class` reaches `1,1,0` and beats the app's typical `0,2,0` class rules with no `!important`. But the cascade checks **importance before specificity** — so if the app declares a property `!important`, your id-scoped non-important rule loses no matter how specific it is, and you must match it with your own `!important` (your higher specificity then breaks the `!important`-vs-`!important` tie). For apps that `!important` their CSS aggressively, **blanket `!important` on every override declaration is an accepted, robust fallback** — it also survives app updates that bump their selectors' specificity; confirm the scope with the user, then apply it uniformly. (See lesson #5 and Phase 5.)

**Never depend on per-instance hash classes.** Apps frequently add a unique scoping hash like `.koala-styles-AYUkxbm05Wmkyd3VlS__123…` that changes on reinstall. Anchor selectors on the BEM-named classes only.

**Inspect before authoring.** Class names, root tag, parent container, and computed styles must come from a live DOM read — not a guess. The chrome-in-chrome MCP is the canonical mechanism.

## Required inputs

Ask for any missing input via a single `AskUserQuestion` call before any code is written.

1. **Live preview URL** — a fully rendered theme preview where the app widget appears. For Shopify themes, this is typically a `…shopifypreview.com/products/<handle>?…` URL or the live storefront. The widget must be visible on this page; if it isn't, the skill's inspection phase fails.
2. **Desktop Figma URL** — `figma.com/design/{fileKey}/...?node-id={a}-{b}` for the target design.
3. **Mobile Figma URL** — same format. Skip only if the user explicitly says the design is single-viewport.
4. **Parent container** — the existing theme snippet/section whose `<style>` block will host the overrides AND whose root `id`/`class` will scope them. Examples: `snippets/product-info-figma.liquid` with id `#ProductInfoFigma-{{ section_id }}`, or `sections/cart.liquid` with id `#Cart-{{ section.id }}`. If unknown, the skill identifies it during Phase 1 inspection.

For Figma URLs: parse `figma.com/design/{fileKey}/{name}?node-id={a}-{b}` → `fileKey={fileKey}`, `nodeId="{a}:{b}"` (convert `-` to `:`). If the URL contains `/branch/{branchKey}/`, use `branchKey` as `fileKey`.

## Workflow

### Phase 1 — Orient (parallel reads)

In ONE message, call in parallel:

- `Read` the parent container file (e.g., `snippets/product-info-figma.liquid`) — locate its existing `<style>` block, the root id pattern, and the position where overrides should be appended.
- `Bash: git log --oneline -10` — check recent commits for prior app-styling work; mirror the existing commit style.
- If the user provided a parent container path, skip the file-discovery sub-step. If not, `Glob` for the snippet that wraps the area where the app widget renders (often `*product-info*`, `*cart*`, `*main-product*`).

### Phase 2 — Live DOM inspection (chrome-in-chrome MCP)

This phase pins down the app's class names, root element, and computed styles. Without it, every selector is a guess.

#### 2a. Load the chrome-in-chrome tools

Use the Skill tool to load `chrome-devtools-mcp:chrome-devtools` for guidance, then `ToolSearch` to fetch the tool schemas:

```
ToolSearch query: "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__javascript_tool"
```

(If `mcp__claude-in-chrome__*` tools aren't available, fall back to `mcp__plugin_chrome-devtools-mcp_chrome-devtools__*` — same workflow, different tool names. The chrome-devtools-mcp variant launches its own Chrome; chrome-in-chrome attaches to an existing session via a browser extension.)

#### 2b. Get tab context FIRST

```
mcp__claude-in-chrome__tabs_context_mcp({ createIfEmpty: true })
```

Capture the `tabId`. **Always call this before any other browser tool** — chrome-in-chrome explicitly requires it once per session. Without it, every subsequent call fails with "no valid tab ID".

#### 2c. Navigate to the preview URL

```
mcp__claude-in-chrome__navigate({ tabId: <id>, url: <preview-url> })
```

If the user denies the navigation prompt, use AskUserQuestion to ask whether they'd like to retry, paste the DOM snapshot manually, or proceed with broad selector patterns. Don't fall back silently to guessing.

#### 2d. Extract the widget's structure with one batched JS query

The single most important call in this skill. Run a JS function that:

1. Collects all candidate elements with broad selectors (`[class*="<app-prefix>"]`, `[id*="<app-prefix>"]`, plus elements containing widget-identifying text).
2. Filters down to the widget root (deepest element that contains all known widget text but isn't broken into smaller parts).
3. Walks the root, collecting all unique class names, child structure, and computed styles for the root element (`backgroundColor`, `border`, `borderRadius`, `padding`, `margin`, `fontFamily`).
4. Returns: `rootTag`, `rootClasses`, `rootParentTag`, `rootParentClasses` (this tells you the scoping anchor!), root computed styles, top class frequencies, and a 4-level skeleton dump.

Example template (substitute the app-specific keyword):

```javascript
(() => {
  const APP_KEYWORD = 'koala';  // substitute the app's class prefix
  const ROOT_TEXT_HINTS = ['Mix & Match', 'Add selected items'];  // 1-3 strings the widget renders

  const candidates = [
    ...document.querySelectorAll(`[class*="${APP_KEYWORD}" i]`),
    ...document.querySelectorAll(`[id*="${APP_KEYWORD}" i]`),
    ...Array.from(document.querySelectorAll('*')).filter(el =>
      ROOT_TEXT_HINTS.some(h => (el.textContent || '').includes(h)) &&
      el.children.length > 0 && el.children.length < 50
    )
  ];

  const seen = new Set();
  const unique = candidates.filter(el => !seen.has(el) && (seen.add(el), true));

  let root = null;
  for (const el of unique) {
    if (ROOT_TEXT_HINTS.every(h => (el.textContent || '').includes(h))) {
      if (!root || el.contains(root) === false) {
        if (root && root.children.length > el.children.length && el.contains(root)) continue;
        root = el;
      }
    }
  }
  if (!root) for (const el of unique) {
    if (ROOT_TEXT_HINTS.some(h => (el.textContent || '').includes(h))) { root = el; break; }
  }
  if (!root) return { error: 'no widget root found', candidates: unique.length };

  const classMap = {};
  const walk = (el, depth) => {
    if (depth > 8) return;
    if (el.className && typeof el.className === 'string') {
      el.className.split(/\s+/).forEach(c => { if (c) classMap[c] = (classMap[c] || 0) + 1; });
    }
    Array.from(el.children).forEach(c => walk(c, depth + 1));
  };
  walk(root, 0);

  const skeleton = (el, depth) => {
    if (depth > 4) return '';
    const tag = el.tagName.toLowerCase();
    const cls = el.className && typeof el.className === 'string'
      ? '.' + el.className.split(/\s+/).filter(Boolean).slice(0, 4).join('.') : '';
    const txt = (el.children.length === 0 && el.textContent)
      ? ' "' + el.textContent.trim().slice(0, 40) + '"' : '';
    let line = '  '.repeat(depth) + tag + cls + txt + '\n';
    Array.from(el.children).slice(0, 6).forEach(c => { line += skeleton(c, depth + 1); });
    if (el.children.length > 6) line += '  '.repeat(depth + 1) + `... (${el.children.length - 6} more)\n`;
    return line;
  };

  const rootStyle = getComputedStyle(root);
  return {
    rootTag: root.tagName,
    rootClasses: (root.className || '').toString(),
    rootParentTag: root.parentElement?.tagName || null,
    rootParentClasses: root.parentElement?.className?.toString() || null,
    rootBackground: rootStyle.backgroundColor,
    rootBorder: rootStyle.border,
    rootBorderRadius: rootStyle.borderRadius,
    rootPadding: rootStyle.padding,
    rootMargin: rootStyle.margin,
    rootFontFamily: rootStyle.fontFamily,
    classCount: Object.keys(classMap).length,
    topClasses: Object.entries(classMap).sort((a,b) => b[1]-a[1]).slice(0, 30),
    skeleton: skeleton(root, 0).slice(0, 4500)
  };
})();
```

Critical fields to read from the result:
- **`rootTag`** — `DIV` is normal; `<APP-NAME>-BLOCK` etc. is a custom element. Either way, light DOM is fine if classes were enumerated. **If `classCount === 0` despite `rootClasses` having values, the widget is using shadow DOM** — see lesson #1.
- **`rootParentClasses`** — this is the anchor for your override scoping. If parent is `pif-cart-section` (which lives inside `#ProductInfoFigma-…`), your selectors scope under that id.
- **`topClasses`** — your override targets. Each BEM-named entry maps to one Figma piece.

### Phase 3 — Fetch Figma design context

In parallel:

- `mcp__plugin_figma_figma__get_design_context` for the desktop URL.
- `mcp__plugin_figma_figma__get_design_context` for the mobile URL.

Extract per-element specs: typography (family, weight, size, line-height, letter-spacing), colors (text, background, border), spacing (padding, gaps, radii), and any state-dependent variants (hover, selected, disabled).

### Phase 4 — Build the class-to-Figma mapping

In a single table, map every BEM class observed in Phase 2 to its Figma equivalent from Phase 3:

| App class | Figma spec |
|---|---|
| `.app__root` | font-family, border, radius, padding, background |
| `.app__heading` | typography token |
| `.app__item` | border, radius, padding |
| `.app__item--selected` | border-color override |
| `.app__cta` | background, padding, radius, hover variant |
| ... | ... |

This table goes verbatim into the plan file. Reviewers can sanity-check it before any CSS is written.

**Specificity check** before you commit to a scoping anchor:
- Compute the app's typical specificity (count classes/pseudo-classes/pseudo-elements in the longest selector you see in their `<style>` blocks via DevTools — usually `0,2,0` or `0,3,0`).
- Compute your override specificity. ID + class = `1,1,0`. ID + class + class = `1,2,0`.
- Confirm yours is higher. If not, widen the anchor or escalate to `:where()` neutralization, NOT `!important`.

### Phase 5 — Verify live (inject candidate CSS + measure)

Before committing overrides to the file — and again after — confirm they reproduce the Figma geometry and typography against the *live* widget. Measure; don't eyeball. This runs in the browser exactly like Phase 2 (fine during plan mode) and is re-run after Phase 7.

**The loop:**

1. Inject ONE `<style>` with a stable id holding your candidate overrides (scoped under the panel id). Overwrite its `.textContent` each pass instead of adding new `<style>` elements, and wipe stale tests first so old rules don't pollute the measurement:
   ```javascript
   document.querySelectorAll('style[id^="kh-override-test"]').forEach(e => e.remove());
   const s = document.createElement('style');
   s.id = 'kh-override-test';
   s.textContent = `#PanelId .app-class { ... }`;
   document.head.appendChild(s);
   ```
2. Measure the element chain with `getBoundingClientRect()` + `getComputedStyle()` and compare to the Figma px tokens (widths, gaps, font-size/weight/line-height, border, radius).
3. Iterate selectors/values until the numbers match Figma.

**Head-vs-body cascade caveat (load-bearing — it costs the most round-trips):**

An injected `<head>` `<style>` **cannot** override a rule that already ships in the theme's body `{% style %}` block at *equal specificity* — the body rule comes later in the DOM, so it wins on source order. Therefore:

- Injection cleanly verifies **new** rules (no deployed twin) and rules that win by specificity or `!important`.
- Injection **cannot** preview *changing an existing deployed declaration* at equal specificity (e.g. `display: block → flex`, `flex: 1 1 auto → 1 1 0`). The injected version silently loses and you measure the OLD value — it looks like your fix "did nothing".
- **Workaround:** force the injected test with `!important` (head `!important` beats body non-important) to confirm the *value/behaviour* works, then make the real change by **editing the existing rule in the file in place** — not by appending a duplicate selector.

**Tab hygiene:** call `tabs_context_mcp` first (Phase 2); re-call it whenever a tool errors "tab no longer exists" (tabs go stale when the user reloads or closes them) and reuse the already-open preview tab rather than navigating a fresh one.

**Reusable measurement helper** — given the panel id and a chain of selectors, returns each element's width / right-edge / computed `flex`/`padding`/`margin`, plus the gaps between a parent's children, so you can spot exactly where a width collapses or a gap is wrong:

```javascript
(() => {
  const P = '#PanelId';                              // the scoping panel id
  const root = document.querySelector(`${P} .app-root`);
  const m = sel => {
    const e = (root || document).querySelector(sel);
    if (!e) return null;
    const c = getComputedStyle(e), r = e.getBoundingClientRect();
    return { w: Math.round(r.width), right: Math.round(r.right),
             flex: c.flex, padding: c.padding, margin: c.margin };
  };
  const gapsOf = sel => {                             // gaps between a parent's children
    const p = (root || document).querySelector(sel); if (!p) return null;
    const k = [...p.children]; const g = [];
    for (let i = 1; i < k.length; i++)
      g.push(Math.round(k[i].getBoundingClientRect().top - k[i-1].getBoundingClientRect().bottom));
    return g;
  };
  return JSON.stringify({
    chain: ['.app-row', '.app-label', '.app-control'].map(s => ({ s, ...m(s) })),
    sectionGaps: gapsOf('.app-stack')
  }, null, 2);
})();
```

Adjust the selectors to the widget. A child that won't fill its parent almost always reveals the culprit here — an app `padding-right` on the row, or a `flex-basis` that isn't `0` (see lesson #15).

**Verify centering — two questions, not one.** Measuring an element's *box center* against the container center is a false signal: a full-width block with left-aligned text has its box center AT the container center, so left-aligned text reads as "centered." Test the **left edge against the ideal centered left** within the container's content box — and for full-width text, also confirm `text-align: center`:

```javascript
const centered = (el, container) => {
  const er = el.getBoundingClientRect(), cr = container.getBoundingClientRect();
  const cs = getComputedStyle(container);
  const padL = parseFloat(cs.paddingLeft), padR = parseFloat(cs.paddingRight);
  const contentW = cr.width - padL - padR, contentLeft = cr.left + padL;
  return Math.abs(er.left - (contentLeft + (contentW - er.width) / 2)) < 4;
};
// A FULL-WIDTH text node returns ~true here regardless of alignment, so for text
// also require getComputedStyle(el).textAlign === 'center'. (See lessons #19 and #20.)
```

**Reach a real mobile viewport.** Resizing the browser window often can't shrink the storefront — the preview renders it fixed-width, or its device toggle nests the store in a (usually same-origin) `<iframe>`. So `window.innerWidth` stays desktop and top-window `document.querySelector` reads the preview *wrapper* (you'll get "0 sections / nothing rendered" — a false alarm). Read INTO the iframe to get a genuine mobile viewport, then run the helper + `centered()` against its `doc`/`win`:

```javascript
const fr = document.querySelector('iframe');
let doc = document, win = window;
try { if (fr && fr.contentDocument) { doc = fr.contentDocument; win = fr.contentWindow; } } catch (e) {}
// win.innerWidth is now the device width (e.g. 390); win.matchMedia('(max-width:47.99rem)').matches === true.
// Run every querySelector / getComputedStyle against `doc` (not the top window).
```

Confirm same-origin first (the `try` guards a cross-origin iframe, which can't be read). This is the only reliable way to verify **mobile** layout/centering here — window-resize can't deliver it. (See lesson #21.)

### Phase 6 — Plan (plan mode)

Write the plan file with these sections:

- **Context** — why, what app, what Figma node, current state vs target.
- **DOM structure observed** — paste the skeleton tree from Phase 2.
- **Goal** — append CSS overrides to `<style>` block in `<file-path>`, single-file change.
- **Files to modify** — typically the parent snippet only.
- **Class-to-Figma mapping** — the table from Phase 4, full.
- **Detailed CSS** — every override block, ready to paste, scoped under the parent container id.
- **Why this works** — the specificity arithmetic, and where you matched the app's `!important` (or applied blanket `!important`) and why.
- **Verified live** — the Phase 5 measurements vs the Figma tokens (widths, gaps, type) that confirm the overrides land.
- **What this does NOT do** — moves widget? changes HTML? Future-proof against app updates? Be explicit about the boundaries.
- **Risk + rollback** — single-file diff, `git revert` reverses cleanly. Future app updates may rename classes (low risk for BEM-using apps, surface as known limit).

On approval, `ExitPlanMode`.

### Phase 7 — Execute

1. `Read` 5–10 lines around the existing `<style>` block's closing `</style>` to capture indentation.
2. `Edit` — append the override block immediately before `</style>`. The `old_string` should include the last few lines of pre-existing rules + `</style>` so the anchor is unique.
3. `git diff --stat` to confirm a single-file change with the expected line count.

Do not commit unless asked.

### Phase 8 — Report

End-of-turn summary:

- **App identified** — the widget's root tag and BEM prefix.
- **Override count** — how many BEM classes mapped, lines added.
- **Files modified** — the single parent snippet.
- **Visual deltas applied** — typography swap, colors, borders, spacing, button styling, etc. (1-line each).
- **Skipped on purpose** — interactive elements (checkboxes, click targets) NOT overridden, and why.
- **Known limits** — future app updates may break overrides; per-instance hash classes intentionally not used as anchors.

## Hard-won lessons (load-bearing — internalize, don't just follow)

These come from real successful runs. Each one costs a real round-trip to discover.

### 1. Light DOM vs Shadow DOM — check first, override later

Modern web-component-based widgets (`<custom-element-name>`) can use shadow DOM, which isolates internal styles and class names from the document. Your CSS selectors won't reach inside.

**The 30-second test**: in the JS query, `document.querySelector('.app-inner-class')` from the page context. If it returns the element, light DOM — proceed normally. If it returns null but the widget visibly renders, shadow DOM — your overrides need `::part()` (if the app exposes parts), CSS custom property exposure (`--app-color: red` declarations), or you're stuck with a JS-time mutation observer + inline styles.

Most Shopify apps choose light DOM for theme-customizability. Confirm before assuming.

### 2. BEM naming is your friend; functional naming is a curse

Apps using BEM (`.app__heading`, `.app__item--selected`, `.app__cta`) give you stable, deterministic selectors mapped to visual purpose.

Apps using utility frameworks (Tailwind-style `.text-lg .font-bold`) or hash-mangled classes (`.css-1a2b3c4`) make overrides much harder. Either fork strategy:

- **For Tailwind utility classes**: target the parent and use cascade — `<container> > .child:nth-child(2)` patterns work but are brittle.
- **For hash-mangled classes**: try data attributes (`[data-component="bundle-card"]`), ARIA roles, or specific text content via `:has(...)` selectors.

Always inventory the class style during Phase 2 — it shapes the plan.

### 3. The per-instance hash class trap

Many apps add a unique class per merchant install for their own style scoping (e.g., `.koala-styles-AYUkxbm05Wmkyd3VlS__4143866229958350875_<hash>`). Two reasons NOT to anchor your selectors on it:

- **Reinstall**: the hash regenerates if the merchant uninstalls and reinstalls the app. Your selectors stop matching.
- **Cross-store portability**: if you reuse this skill on another store, the hash differs there too.

Always anchor on the BEM-named class. The hash class is fine to ignore.

### 4. The parent class is your scoping anchor

The JS query returns `rootParentClasses` — that's the immediate ancestor of the widget. If the widget is inside your existing scoped panel (e.g., parent class is `pif-cart-section`, which is inside `#ProductInfoFigma-{{ section_id }}`), use the panel id as the scoping anchor.

If the widget renders OUTSIDE your snippet (e.g., directly under `<body>` because the embed JS appendChild'd to body), you need a different strategy:

- Find a higher-level theme container that wraps the widget (e.g., `#shopify-section-<id>`).
- If no theme container wraps it, scope under `body` and accept lower specificity — but understand any other body-scoped rules in the theme can compete.
- Last resort: `!important` (acknowledged as last resort, used surgically).

### 5. Specificity math is the override's load-bearing assumption

Every override's effectiveness rides on this calculation. The cascade resolves in three tiers **in order — origin/importance → specificity → source order** — so importance is checked *first*: an `!important` declaration beats any non-important one regardless of specificity.

- App: `.app__cta { background: orange !important; }` → `(0,1,0)` **important**.
- You: `#PanelId .app__cta { background: blue; }` → `(1,1,0)`, not important → **LOSES** (importance outranks specificity).
- You: `#PanelId .app__cta { background: blue !important; }` → both important, so specificity breaks the tie, `(1,1,0) > (0,1,0)` → **WINS**.

When neither side uses `!important`, specificity then source-order decides:

- App's selector: `.app__cta:hover` → specificity `(0, 2, 0)` (one class + one pseudo).
- Your selector: `#PanelId .app__cta:hover` → `(1, 2, 0)`. **Wins.**
- App's selector: `.app__cta.app__cta--primary:hover` → `(0, 3, 0)`.
- Your selector: `#PanelId .app__cta` → `(1, 1, 0)`. **Loses** — needs to be `#PanelId .app__cta.app__cta--primary` or `#PanelId .app__cta:hover` to compete.

Run a quick mental specificity check on each override before writing it. The app's `<style>` block in DevTools shows their selectors verbatim — copy the most-class-heavy one and add 1 to the id-count. **Scan it for `!important`, too** — if the app marks a property you're overriding, you must match it (see "The rule" and lesson #14).

### 6. Hover/active/disabled states need separate rules

Easy miss: you override `.app__cta { background: blue; }` and the button looks blue at rest, but on hover it reverts to the app's orange because their `:hover` rule has equal-or-higher specificity than your base rule.

**Always write a matching `:hover` (and `:active`, `:disabled`, `:focus-visible` if applicable) override block.** Use `:not(:disabled)` to avoid clobbering disabled-state appearance.

### 7. Custom elements ARE real DOM, despite looking weird

`<koala-bundle-block>` is a Web Component. It's not HTML you wrote, but it's HTML you can style. Don't be intimidated by the unfamiliar tag name — class-based selectors apply normally as long as the element uses light DOM.

A 30-second test for any custom element: `document.querySelector('koala-bundle-block .child-class')` from the console. Returns an element → your CSS will reach it.

### 8. The widget might not have a stable root — query by content

Some apps don't put a single class on their root element; they use a wrapper `<div>` with no distinguishing class and rely on internal classes for styling. If `[class*="<app-prefix>"]` matches multiple elements at different nesting levels, pick the deepest one that contains ALL widget-identifying text. Use `Array.from(...).filter(el => h1 && h2 && h3)`-style queries with multiple text hints.

The provided JS query template handles this with `ROOT_TEXT_HINTS.every(...)` — pass 2-3 strings the widget renders that won't appear elsewhere on the page.

### 9. Don't override interactive elements you don't fully understand

Checkboxes, radio buttons, drag handles, expandable arrows — these have internal click handlers, ARIA semantics, focus management. Restyling them risks breaking interaction or a11y.

Safe overrides: visual-only properties on these elements (color, border-radius). Risky overrides: `display`, `pointer-events`, replacing a checkbox with a custom div. Skip the latter unless the user explicitly accepts the risk and you've tested click-areas + screen-reader behavior.

For the Koala bundle work, the `.koala-deal__mix-match-checkbox` was intentionally left untouched. Lesson: when in doubt, skip the element and document why in the plan's "What this does NOT do" section.

### 10. Use the theme's unit convention for cascade-friendliness

If the surrounding theme uses rem-based sizes (`1.6rem` for 16px, etc.), your overrides should too. Mixing units in one stylesheet creates confusion later AND loses the global root-font-size scaling that the theme might apply.

Quick check: read 5-10 lines of the existing `<style>` block in the parent snippet. If it's rem-based, override in rem. If it's px-based, override in px. Don't mix.

### 11. Append at the end of `<style>` — last-cascade tiebreaker

When specificity ties, the rule declared later wins. Append the override block at the very end of the parent's `<style>` block (before `</style>`), not interleaved with existing rules. Two benefits:

- **Cascade tiebreaker** — for any equal-specificity collision, your override wins.
- **Diff cleanliness** — the addition is one contiguous chunk, easy to review and revert.

### 12. The app's JS may re-render — pure CSS handles that automatically

If the app re-mounts its widget (cart updates, variant changes, hot reload), pure CSS overrides re-apply automatically because the cascade re-runs on each render. JS-based DOM manipulation (e.g., a MutationObserver that moves elements around) doesn't have this property — it must re-run on every re-render.

Prefer CSS-only overrides whenever possible. Reach for JS only when CSS can't reach (e.g., need to reorder children, can only express via DOM tree manipulation).

### 13. Mobile breakpoint mismatch — verify both viewports

Apps often ship their own mobile-specific CSS via media queries. Your override at `(min-width: 1024px)` desktop won't apply on mobile, so the app's mobile rules win — and may not match Figma mobile.

**Always test both viewports**, and write a matching mobile override (`@media (max-width: 1023px)` or your theme's breakpoint) when desktop and mobile Figma diverge.

**Flex-axis trap:** a width-fill fix like `flex: 1 1 0` behaves differently per direction — on a `flex-direction: column` element it grows the item *vertically*, not horizontally. So when mobile stacks (column) but desktop is a row, keep width-fill fixes (and the out-of-flow repositioning of lesson #16) inside the desktop `@media` so they don't distort the stacked mobile layout. To actually *obtain* a mobile viewport for measurement (window-resize often can't), see lesson #21.

### 14. Injected test CSS can't beat the theme's body `{% style %}` at equal specificity

When you verify overrides by injecting a `<style>` into `<head>` (Phase 5), it loses to a rule already shipped in the theme's body `{% style %}` block at *equal specificity* — body comes later in the DOM, so source order hands it the win. Injection therefore can't preview *changing* an existing deployed declaration (`display: block → flex`, `flex: 1 1 auto → 1 1 0`): you'll measure the OLD value and think your fix did nothing.

Confirm the value with a forced `!important` injection (head `!important` beats body non-important), then make the real change by **editing that exact rule in the file** — not by appending a second copy of the selector.

### 15. Reaching the container edge: flex-grow fills the *content box*, not padding

A child won't reach its parent's edge if the app put `padding` on the parent — `flex-grow` only distributes free space *inside* the content box, never into padding. Zero the app's `padding` (e.g. a stray `padding-right`) on that row. Two more traps on the same problem:

- `flex-basis: auto` grows an item from its *content* width (so it barely expands). Use `flex: 1 1 0` (basis `0`) to make it consume all free space.
- A filled flex *container* is not a filled *child*: an inner control (a `<select>`, an `<input>`) keeps its intrinsic width unless you give it `width: 100%`. Pair it with `box-sizing: border-box` so its own padding doesn't overflow the container.

Walk the width chain with the Phase 5 measurement helper to find which level collapses.

### 16. An app control pinned in a full-height flex column caps your content width

When the app lays the card out as flex siblings `[control-column | content-column]` (e.g. a radio in its own column), the content column can never reach the card's far edge — the control's column occupies it for the full height. Figma usually shows that control as a top-corner *overlay*, not a column. Reproduce that by taking the control **out of flow**: `position: absolute; top/right` on the control, with `position: relative` on the card as its anchor. The content column then spans the full width. Scope this to the breakpoint that needs it (lesson #13) — mobile often wants the control back in flow. (Related trap: a child's own `align-self` overrides the parent's `align-items`, so centering the parent doesn't reach it — see lesson #20.)

### 17. Per-variant styling via `:has()`

Apps frequently render the same class for every variant/state and differentiate only by a child marker. Branch on that descendant with `:has()`:

```css
#PanelId .option:has(.one-time-price) .label { font-weight: 400; }
#PanelId .option:has(.subscription-price) .price { font-weight: 600; }
```

Bonus: `:has()` carries the specificity of its argument, so `…:has(.x) .label` `(1,2,0)` also out-specifies a shared `… .label` `(1,1,0)` rule you wrote earlier.

### 18. Deploy lag — the preview trails your commits

A Shopify theme connected to GitHub redeploys the preview on **push**, not on your local commit. A freshly committed fix won't appear in the preview until that deploy syncs — then a hard-refresh. Live injection (Phase 5) shows the fix *immediately*, so use it for the feedback loop and tell the user to let the deploy catch up before judging the deployed result (otherwise you'll both be looking at the previous build).

### 19. Measuring centering: the box-center lie

`(rect.left + rect.width/2) − containerCenter ≈ 0` reports "centered" even when a full-width block's text visibly hugs the left — because the *box* spans the full width, its center sits at the container center regardless of where the text sits inside it. This produces confident false positives (it cost three "it's centered now" claims that weren't).

Test the **left edge against the ideal centered left** instead: `|rect.left − (contentLeft + (contentW − rect.width)/2)| < ~4px`. And for a full-width text node that *also* passes that test, require `getComputedStyle(el).textAlign === 'center'`. Two questions, always: is the **box** centered within its container, and is the **text** centered within the box?

### 20. Centering levers: which property actually moves it

Centering a flex child is not one-size-fits-all — the app fights each lever differently:

- **`align-self` beats the parent's `align-items`.** If the app sets `align-self` on a child (e.g. a price wrapper at `align-self: baseline`), centering the parent's `align-items` won't touch it. Override the child's own `align-self: center`.
- **Full-width vs content-width picks the lever.** On a narrow (mobile) card, a label whose one-line text exceeds the card fills it (caps + wraps) → it's effectively full-width, so `align-items`/`align-self: center` do nothing; you need `text-align: center`. The *same* label on a wide (desktop) card is content-width and centers via `align-items`. One element can need different levers per breakpoint.
- **Apps hard-set `text-align: left`** on labels/values, overriding the center inherited from a container. Override it explicitly.
- **Strip app defaults at EVERY breakpoint.** A `padding` / `text-align` / `margin` you neutralized on desktop still applies on mobile (a deliver row's `padding-right: 16px`, only stripped on desktop, offset the mobile centering by half its value). A fix scoped to one breakpoint leaves the other broken (see #13).

### 21. A same-origin iframe preview is a real mobile viewport

Resizing the browser window often can't produce a mobile viewport — the preview renders the store at a fixed width, or its device toggle nests the store in a usually-same-origin `<iframe>`. Two consequences:

- **Top-window `document.querySelector` reads the wrapper, not the store** — you get `0` sections / "nothing rendered" false alarms. The store is inside the iframe.
- **That iframe is a genuine mobile viewport.** `const fr = document.querySelector('iframe'); fr.contentWindow.innerWidth` (e.g. `390`) and `fr.contentDocument` let you read computed styles and measure media-query-dependent layout that window-resizing couldn't produce. Verify mobile centering INSIDE the iframe.

Guard with `try { fr.contentDocument }` — a cross-origin iframe can't be read (fall back to asking the user to open DevTools' device mode and report). See Phase 5's "Reach a real mobile viewport."

### 22. The Figma is drawn on white — light tokens vanish on a tinted live card

A design's light tokens (a near-white border like `#f5f5f5`, a pale avatar/chip fill like `#fdf6e3`) read fine against the Figma's white frame but **disappear** when the live widget sits on a tinted card — a merchant `*_background` setting, a brand tint — whose color is only a few units away (`#f5f5f5` border on an `#f5f5f0` card). Symptom: "the border/element isn't showing" while computed styles confirm it IS applied. Diagnose by comparing the element's computed color to the **live background color**, not by eye. Fix: either darken each light token until it reads on the tint (drifts from the Figma value), or — cleaner — restore the surface to the Figma's (usually `#ffffff`), which makes every light token render as designed at once. Changing the card background may override a merchant setting, so confirm first.

### 23. Faked label text in an absolutely-positioned `::before` doesn't size its box — and flex can crush it

Apps often hide the real content and inject a label via a fixed-width element's `::before { position: absolute }` (common for histogram/rating-row labels). The box does NOT grow to fit the text, and `flex-shrink` can squeeze it even below its set width — so the absolute text overflows and overlaps the next flex item (you'll measure a *negative* gap). Fix: set the label box to the exact Figma label width and add `flex-shrink: 0`. Measure the real gap from `label.left + measuredTextWidth` (canvas `measureText` at the computed font), not from the box's right edge.

### 24. App avatar/icon glyphs are usually pseudo-elements painted with background-COLOR

An "avatar" or "icon" showing a silhouette plus a small badge is frequently an empty element (`querySelector` finds no children, computed `background-image` is `none`) whose parts are `::before`/`::after` drawn with `background-color` + `border-radius`. Identify each by probing its `position`/`top`/`left`/`backgroundColor` — an `absolute` corner pseudo in the brand color is the badge. Hide the unwanted part with `::after { display: none }`. CSS can't inject text the app never renders: if the Figma shows an initial letter where the app draws a silhouette, you can match the circle and color but not the letter — say so rather than chasing it.

### 25. Element trapped in the wrong container → relocate with a tiny idempotent script (not a magic-number offset)

When the design needs an element where the app renders it in a *different* container (earlier in the DOM, or a narrower fixed-width column), the cascade can't reach it — `position: absolute` only anchors to a positioned ancestor and forces a hardcoded `top` that breaks across content/viewports (measure to prove this before accepting it). The robust fix is a theme-side relocation (NOT app-side): query the node and its target, `appendChild` only when `node.parentElement !== target` (idempotent — the guard prevents an infinite observer loop), and re-run on app re-render via a `MutationObserver` on the stable theme wrapper. Pair with higher-specificity flex CSS on the destination row. This crosses CSS-only into theme-JS — get explicit user opt-in. (Contrast lesson #16, which stays in-flow within a single parent.)

### 26. Preview a *changed* deployed rule by injecting at +1 specificity

Lesson #14 means a head-injected test can't beat a body `{% style %}` rule you're changing at equal specificity, so the preview shows the OLD value and your edit looks like a no-op. To preview the real result before pushing (while the stale shipped rules are still live), inject the test scoped under one extra ancestor (`.parent .app-class` vs `.app-class`) so it out-specifies the stale rule — then make the real edit in-file at the file's normal specificity. The boosted scope is a preview device only; don't ship it.

### 27. Reuse a finished override across sibling/base themes via git blob hash

Agencies clone a base theme per client, so a widget's host snippet is often byte-identical across stores. Before re-deriving overrides for a sibling/base theme, confirm the host file is identical: `git hash-object <dest-file>` vs the source's `git rev-parse <ref>:<path>`. If the blobs match, replicate the finished file verbatim (`git show <ref>:<path> > <dest>`) and re-hash to confirm parity — far safer than re-applying a dozen edits by hand. Flag that hardcoded design tokens (brand colors, a forced white surface) carry the *source* store's design; adjust if the destination brand differs.

## Anti-patterns

- **Using `!important` blindly, without specificity math.** Reflexive use is still discouraged — do the math first. But **matching the app's `!important` is required** (importance beats specificity), and blanket `!important` across the whole override block is an accepted fallback for apps that aggressively `!important` their own CSS (confirm scope with the user first). See "The rule" and lesson #5.
- **Targeting per-instance hash classes** (e.g., `.koala-styles-<hash>`). Anchor on BEM names instead.
- **Editing the app's HTML or JS.** Out of scope. App-injected DOM is your override target, not your edit surface.
- **Skipping live DOM inspection** and guessing at class names. Apps' actual class names rarely match what you'd guess from their docs.
- **Skipping the shadow DOM check.** Five seconds of `document.querySelector(...)` from the console saves an hour of "why don't my overrides apply?"
- **Overriding interactive elements** (checkboxes, drag handles, radio buttons) without testing a11y/click-area afterward.
- **Putting overrides in a separate file when the parent snippet's `<style>` block already exists.** Adds a stylesheet HTTP request for nothing — the snippet is rendered inline anyway.
- **Mixing units** (px and rem) within one override block. Match the surrounding code's convention.
- **Overriding `display: none` to hide app elements** without confirming with the user. Hiding parts of a third-party widget can break the app's internal logic. Ask first.
- **Forgetting hover/active state overrides.** Base rules win at rest, lose on hover if the app has its own `:hover` rules. Mirror every state.
- **Authoring CSS in PR descriptions instead of the file.** Your overrides go IN the snippet's `<style>` block, not in commit messages or chat.
- **Targeting the per-section_id'd panel only without a fallback.** If the section id changes (theme editor regenerates section keys when sections are duplicated), your selectors stop matching that one instance. The override CSS in a snippet is rendered per-section-instance with the matching id — this is fine. But for embedded SECTION blocks (not snippets), prefer scoping under a stable class on the parent rather than `#shopify-section-{{ section.id }}` for portability.
- **Running multiple agent sessions in one shared git working tree.** Their commits race: a staged file gets swept into another session's commit (landing under the wrong message), and a pre-commit `lint-staged` stash/restore can clobber your *uncommitted* edits. Use a separate git worktree per concurrent session, and commit promptly (staged-only) so in-progress work isn't left exposed. Stage explicitly by path (`git add <file>`) — never `-A` — so you can't bundle another session's files.
- **Trusting a screenshot over measurement.** The browser-MCP screenshot endpoint can time out or lag behind the DOM. Treat `getBoundingClientRect()` + `getComputedStyle()` as the source of truth and screenshots as confirmation, not the primary check.

## Quick reference

### Scoping anchor decision tree

```
What's the parent of the widget root (from Phase 2 query)?
  ↓
Is the parent inside an existing theme snippet/section that has a stable id?
  → YES: scope under that id
       (e.g., #ProductInfoFigma-{{ section_id }} .widget__class)
  → NO ↓
Is the parent inside #shopify-section-{{ section.id }}?
  → YES: scope under that
  → NO ↓
Is the widget directly under <body>?
  → Use a stable class on <body> if the theme provides one
       (e.g., .template-product .widget__class)
  → If still no anchor available
       → Last resort: !important on each rule, accept the cost
```

### Figma → CSS property cheat sheet

| Figma | CSS |
|---|---|
| `font-['<Family>:<Weight>']` size N px | `font-family: "<Family>", sans-serif; font-weight: <weight>; font-size: <N>rem;` (or px to match theme) |
| `bg-[#hex]` | `background: #hex;` |
| `border border-[#hex]` | `border: 1px solid #hex;` |
| `border-[<N>px] border-[#hex]` | `border: <N>px solid #hex;` |
| `rounded-[<N>px]` | `border-radius: <N>rem;` (or px) |
| `p-[<N>px]` | `padding: <N>rem;` |
| `px-[<X>] py-[<Y>]` | `padding: <Y>rem <X>rem;` |
| `gap-[<N>px]` | `gap: <N>rem;` |
| `flex flex-col items-start gap-[N]` | `display: flex; flex-direction: column; align-items: flex-start; gap: <N>rem;` |
| `text-[<color>]` | `color: <color>;` |
| `line-through` | `text-decoration: line-through;` |

### Commit message format

```
Restyle <App Name> widget to match Figma <Figma node label>

<One-paragraph body describing the override scope:>
- BEM class mapping table summary
- Specificity strategy (id-scoped / matched the app's !important / blanket !important / etc.)
- What the override does NOT do (HTML untouched, no JS, no app code)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```

Real example (post-Koala-bundle work):

```
Restyle Koala bundle widget to match Figma Complete The Set design

Adds CSS overrides scoped under #ProductInfoFigma-{{ section_id }} for
the <koala-bundle-block> custom element rendered by the Upsell Koala
Bundles theme embed. Live DOM inspection confirmed Koala uses light DOM
with BEM-style class naming so standard selectors apply without shadow
piercing. Specificity (1,1,0) beats Koala's class-only rules (0,2,0)
so no !important is needed. Does not move the widget or change Koala's
HTML structure. The checkbox element is intentionally left untouched
to preserve the app's click-area detection and accessibility semantics.
```

### Commonly-overridden Shopify app prefixes (heuristic)

| App | Class prefix | Root tag |
|---|---|---|
| Upsell Koala Bundles | `koala-deal`, `koala-bundle` | `<koala-bundle-block>` |
| Yotpo Reviews | `yotpo-`, `yotpo-widget-` | `<div>` |
| Judge.me | `jdgm-`, `jdgm-widget-` | `<div>` |
| Loox | `loox-`, `loox-rating` | `<div>` |
| Stamped | `stamped-` | `<div>` |
| One-Click Upsell (Zipify) | `ocu-`, `zipify-` | `<div>` |
| ReConvert | `rc-`, `reconvert-` | `<div>` |
| BOLD Bundles | `bold-`, `bundle-` (generic) | `<div>` |

This list is heuristic, not exhaustive — always verify via Phase 2 inspection. Apps update their prefixes occasionally.

## Out-of-scope (escalate to user before doing)

- **Moving the widget to a different position on the page.** That's `shopify-update-existing-section-from-figma` territory if the widget IS first-party, or a JS DOM-relocation effort with its own complexities for app-injected widgets. Either way, separate scope.
- **Changing the widget's behavior** (interaction, click handlers, copy text). The app owns those — surface as a separate request.
- **Adding new schema settings to the app's block.** You don't own the schema. If the user wants merchant-configurable styling, that's a feature request for the app developer.
- **Localizing the widget's text.** Apps usually have their own translation system; surface as a separate concern.
- **Hiding the widget conditionally.** Use the app's own visibility settings (in their admin) or the theme embed's `disabled: true` flag — not CSS `display: none`, which can leave dead DOM.
