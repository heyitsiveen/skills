# Changes that regressed

Changes earlier speed sessions made that cost score, broke the store, or bought nothing, with what happened. They come from the retro of eight sessions on seven client stores, most on the Golden theme; stores are not named.

Check every plan item against this list before you write it. An item may touch the same area as an entry only when it follows that entry's **Plan** line, and its `cause` or `effect` says how it does.

## Score and layout

**R1. Deferring theme CSS** (`media="print"` with an `onload` swap, or any async stylesheet).
- A store targeting 90 fell from 84 to 65 with CLS 0.373.
- Another reached CLS 0.891, which read as 0.005 on preview-URL Samples because their slower timing hid it. Undoing the deferral took that store from 38 to 71.
- **Plan:** keep theme CSS render-blocking. Collapsing many stylesheets into fewer requests is fine, within R3.

**R2. Swapping lazysizes for native lazy loading across the theme.**
- One store: 66 with CLS 0.288, then blank product cards (`src=""`), because callers passing a media-condition `sizes` made `image_url` error.
- Another store's six-change bundle that included it lost every interleaved pair: 76/69, 80/77, 79/75, 81/79.
- **Plan:** change only the above-the-fold images (known defect D2), and keep lazysizes everywhere else, off-canvas menus included: their images sit in flow before their scripts run.

**R3. Inlining a large stylesheet into the HTML.**
- `inline_asset_content` silently refuses an oversized asset and writes an HTML comment instead: inlining a 26 KB `critical.css` dropped the base stylesheet, with no push error and no console error, just an unstyled page.
- On another store, inlining 27 KB delayed the hero's discovery and LCP went from 6 s to 7.8–14.6 s.
- **Plan:** keep large CSS in files. Confirm the rendered page styles, not only the push.

**R4. Splitting the hero preload by breakpoint, or preloading above the viewport tag.**
- Lighthouse evaluates preloads before it applies mobile emulation, so a desktop preload matched the desktop-sized window and fetched the 1600 w image on every Sample.
- A preload placed above `<meta name="viewport">` resolved its `imagesizes` against the wrong viewport and downloaded the hero twice (173 KiB).
- **Plan:** at most one hero preload, placed after `<meta name="viewport">`.

**R5. `content-visibility`.**
- On offscreen sections: LCP rose to about 12 s.
- On the closed mobile-menu sheet: it broke keyboard focus in the live mobile menu, found only after going live.
- **Plan:** treat it as high risk; the smoke check's keyboard-menu step exists because of this entry.

**R6. A lazily rendered mobile drawer through an alternate view.** It removed 114 KB ahead of the hero and gained nothing. **Plan:** spend Rounds elsewhere.

**R7. Lazily initialising a carousel.** A 286 px layout jump. **Plan:** keep carousels initialised at load.

**R8. An eager hero exposing a layout shift.** Not a bad change but a trap that follows a good one (D2):
- About 0.33 CLS in 2 of 17 Samples, from a group block reordering its children on mobile with flex `order`; writing the markup in mobile order removed it (0.004, 0.006, 0, 0, 0).
- 0.928 on one store and 0.886 on another, from a transparent header that pulls the first section up by a header height a script sets after load.
- **Plan:** every D2 Round must show no CLS loss across its pairs. Fix the shift itself (DOM order, the header height reserved in CSS) in its own item.

## Breakage

**R9. Multi-line `{%- # … -%}` comments whose later lines do not start with `#`.** `shopify theme check` passes them, but Shopify's parser rejects them: "Liquid syntax error … Each line of comments must be prefixed by the '#' character". One reached a store's main branch; another turned a preview home page into a 404. **Plan:** write `{% comment %}…{% endcomment %}`, or start every line with `#`.

**R10. Counting with `{% increment %}` to find "the first image".** The counter restarts inside every `{% render %}`, so every image would have turned eager; caught in a sandbox. **Plan:** pick above-the-fold images by `section.index` or `forloop.index`.

**R11. Loading Swiper asynchronously.** Sections call `new Swiper()` inline and bail when it is missing, so it would have silently killed every carousel; caught before shipping. **Plan:** keep Swiper loaded before the sections that call it.

**R12. Deleting assets in the same change that repoints the layout.** Under GitHub's partial sync, nine stylesheets returned 404 on the live store until the sync caught up. **Plan:** delete dead assets in a later Round than the one that stops using them.

**R13. Payment icons rebuilt as lazy `<img>` tags.** The icons shipped with wrong alternative text ("Master", "Shopify pay"), an accessibility regression on the live store. **Plan:** keep every element's accessible name; the accessibility-score check catches a drop.

**R14. Writing `config/settings_data.json`** to switch a preload or priority setting on. That file holds the merchant's own edits, and going live would overwrite them; the program refuses any Round that touches it. **Plan:** use a schema default or a code-only choice, such as D2's `section.index` route.

## Outside this skill

These moved scores in earlier sessions but change what the merchant's apps and tags do, which is the merchant's call (ADR 0010). The plan never includes them:

- removing a feedback widget's script, or deferring it until interaction
- delaying Google Tag Manager or Clarity until the first interaction
- switching app embeds off in `config/settings_data.json`

## Mixed: measure, never assume

- **Font preload:** one store kept it (CLS 0.003 → 0, +2); another reverted it.
- **Gating scripts by `request.page_type`:** part of a bundle that lost every interleaved pair, so its own effect is unknown.
