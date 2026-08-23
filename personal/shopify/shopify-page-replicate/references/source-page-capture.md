# Reading a Source page in a browser

The procedure the `page-extractor` follows to reach a **Source page**, capture it, and read
its computed styles. Salvaged from `shopify-migrate-page-to-new-theme`, whose live-capture
step is the one part of it worth keeping.

Read this in full before opening a browser. Every step below is load-bearing: a skipped
scroll loses the lazy-loaded half of the page, and an unsuppressed page-builder bar lands in
the capture.

## 1. Reach the page

The run is given a URL. It may be public, or a preview URL for an unpublished **Source
theme** (`?preview_theme_id=<id>`), and the store may be password-protected.

- **Append `?pb=0`** to every URL. Several page-builder apps inject a floating toolbar into
  the storefront; `pb=0` suppresses it. Without it the toolbar appears in both screenshots.
- **A closed store** returns the password page. Ask the user for the storefront password
  ONCE, submit it, and confirm the page renders before continuing. Never guess a password.
- **The URL does not resolve** — a 404, a redirect to the homepage, or the password page
  after a submitted password: STOP and report the URL and what came back. Never try a
  neighbouring URL and capture whatever answers.
- **The handle is unknown**, or the run was given a template name rather than a URL: fetch
  `/sitemap.xml`, follow the `sitemap_pages_*` / `sitemap_collections_*` child, and match.
  A page's live handle often differs from its template suffix — template
  `page.30-days-of-wellness.json` serving live handle `30-days-wellness-plan` is normal, so
  the two are matched by title, not assumed equal.
- **Derive the source template from the page**, not from the user: the page's own
  `Shopify.template` (or the `template--` prefix on its section ids) names it.

## 2. Fix the clip boundary

Only the template's own sections are read. The header, the footer, announcement bars, cookie
banners and any other section-group output are outside the comparison and outside the
capture.

Find the element that wraps exactly the template's sections — usually `#MainContent`, `main`,
or the common parent of the `#shopify-section-template--…` elements. Confirm it by listing
every `#shopify-section-*` id inside it and every one outside it: the inside list is the
template's sections in render order, and the outside list must hold only section-group
output.

Record the selector in the **Design spec**. Every later capture of the result uses the
Target theme's equivalent boundary, so the two comparisons are of the same region.

## 3. Capture

Per breakpoint — 1440 px, then 390 px, both fixed:

1. Set the viewport width. (Desktop Chrome enforces a ~494 px minimum window width; the
   viewport itself still goes to 390, which is what matters.)
2. **Scroll to the bottom** in steps, then back to the top. This triggers every lazy-loaded
   image, video, and app widget. A capture taken without it shows placeholders.
3. Wait for `document.fonts.ready` and network idle.
4. Disable animations and transitions.
5. Screenshot the clip boundary, not the full page.

## 4. Read the computed styles, section by section

One script per breakpoint, written to a file in the temp working directory and run there,
rather than a script per element. For each `#shopify-section-*` inside the clip boundary,
walk its subtree and record, per element that carries text or a visible box:

- the section's id, its `type` where the DOM exposes it, and its index in render order
- rendered text, verbatim — including typos, casing, em-dashes and leading spaces
- typography: `font-family`, `font-size`, `font-weight`, `line-height`, `letter-spacing`
- colors: `color`, `background-color`, and any gradient or image background
- box: `padding`, `margin`, `gap`, `width`, `height`, `border`, `border-radius`
- layout: `display`, `flex-direction`, `grid-template-columns`, `align-items`,
  `justify-content` — the facts the desktop/mobile difference table is built from
- media: every `img`/`video` `src` and its rendered `width`×`height`
- app-owned regions: the element and the app it belongs to, flagged rather than described

**CSS custom properties, where they exist.** Read the custom properties in scope on each
section wrapper and on `:root`. A value that resolves from `--color-accent` is closer to
design intent than the hex it happens to compute to, and it is what the Fidelity forecast
matches against the Target theme's globals. Record both: the property name and its computed
value.

**What the DOM knows that the template JSON does not.** App blocks render their own copy
(review counts, prices, bundle text). Theme defaults produce visual quirks no setting
declares — a panel that renders on black although its `background_color` is transparent.
Both are read from computed styles, never inferred from settings.

## 5. Structure, from the Source theme where it is reachable

A Shopify CLI pull of the Source theme's `templates/` and `sections/` gives the section
`type` and the `order` array as the theme actually holds them, rather than as the DOM
implies. Attempt it; it is an upgrade and never a requirement. Where it is unavailable or
unauthenticated, the DOM's section ids and order carry the same facts less precisely, and
the run continues on those with the downgrade recorded in the Design spec.

Never ask the client for their theme code. A run blocked on an email is a run that does not
happen.
