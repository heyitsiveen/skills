# Known Golden theme defects

Defects in the agency's Golden theme that every store built on it inherits, each with the fix that worked on those stores and what it bought. The decision program's `diagnose` runs every detection rule below and prints a `DEFECT` line per entry; this file is what you plan from.

- **Plan every `DEFECT … found` entry before any other item**, in this file's order. One plan item may fix several entries when they ship together (D1 with D2 and D3 is the proven bundle); name each in its `defects` list.
- **Every D2 item carries D1.** A Round tests its item on top of the Rounds kept before it, and any earlier item may be removed, so each item that fixes D2 carries D1's fix and names D1, even when an earlier item carries it too: once that one is kept, the token is already there. `plan --items` refuses a D2 item without D1 while D1 is found.
- **A store not on Golden** prints `DEFECT none`. Plan from the Lighthouse findings and the theme code alone.
- **Evidence** comes from the retro of eight earlier speed sessions on seven client stores, six of them on Golden. Stores are not named. A single Sample proves little: treat a figure marked "single Sample" as a direction, and an interleaved pair result as the measured effect.

**Fixed in Golden** is read by the program. It stays `not yet` until the Golden theme ships the fix upstream; then write the first Golden version that carries it, for example `3.1`. A store whose Golden version is at least that one skips the entry's check.

Every Golden client reports `theme_version` 3.0 today, fixed or not, so today every check runs on every Golden store.

## D1. The image snippet's eager-loading flag ignores `false`

**Fixed in Golden:** not yet

**What it is.** `snippets/responsive-image.liquid` reads its loading flag with

```liquid
assign lazy_loading = lazy_loading | default: true
```

Liquid's `default` replaces `nil`, `false` and empty alike, so a caller passing `lazy_loading: false` still gets `true`. Every image the snippet renders is lazy, the hero included. No Golden caller passes `false` today, so the defect is latent until a fix needs an eager image: it is what D2's fix trips over first.

**Detection.** After stripping Liquid comments (nested ones too, since Golden keeps commented-out legacy copies of this snippet), `snippets/responsive-image.liquid` still assigns `lazy_loading` with `default: true` and no `allow_false: true`.

**Proven fix.** One token:

```liquid
assign lazy_loading = lazy_loading | default: true, allow_false: true
```

`unless lazy_loading == false … assign lazy_loading = true … endunless` is an equivalent form some stores used.

**Measured effect.** None on its own; it is what makes an eager image possible. It shipped inside every D2 win below. Plan it in every item that fixes D2.

## D2. The hero image ships as a lazy-loader placeholder

**Fixed in Golden:** not yet

**What it is.** Because of D1, the snippet's lazy branch renders every image, the LCP image included, as a 20 px stub for the lazysizes script:

```liquid
src="{{ initial_src }}" data-src="…width: 1200…" data-srcset="…" data-sizes="auto" loading="lazy"
```

with `initial_src` at `width: 20`, the `lazyload` class and `fetchpriority` left at `auto`. The browser cannot discover the real image until the lazysizes script has run, so the LCP waits for it. This hits the home hero (`blocks/media.liquid`, which passes no loading argument), the first collection cards and the product gallery's first image. A variant: a hero set as a section background (`background-image: url(… width: 3840)` in `sections/section.liquid`) is late-discovered whatever the snippet does; Shopify's guidance is an `<img>` for LCP content.

**Detection.** Either rule fires it.

- **Per page, from the baseline Samples:** in at least three of the page's five mobile Samples, Lighthouse's LCP request discovery check fails, and the LCP element carries a lazysizes class (`lazyload`, `lazyloaded` or `lazyautosizes`) with `data-src` or `data-srcset`. The `DEFECT` line names the pages.
- **Home, from the repo:** `responsive-image` still has the 20 px stub path, and no `render 'responsive-image'` in `blocks/media.liquid` passes `lazy_loading:`, `eager_load:`, `priority:`, `priority_loading:` or `fetchpriority:`.

**Proven fix.** An eager path for above-the-fold images, shipped with D1 and D3:

1. In `responsive-image`, for an eager image render a real `src` and `srcset`, `loading="eager"`, `fetchpriority="high"` and a real `sizes` (default `100vw`, never `auto`), and drop the `lazyload` class and the `data-*` attributes.
2. Choose the eager images in code, which leaves template JSON untouched: in `blocks/media.liquid`, make the first section's media eager and high-priority, then pass both values to the snippet.

   ```liquid
   assign image_lazy = true
   assign image_priority = 'auto'
   unless section.index > 1
     assign image_lazy = false
     assign image_priority = 'high'
   endunless
   ```

   The other proven route is a merchant setting ("Above the fold") switched on for the hero in `templates/index.json`. That is a template JSON change, which the report flags for review before going live.
3. Keep lazysizes for every other image (see regressions R2).

Watch for these in the item's Round:

- A hero with separate mobile and desktop `<img>` elements downloads both once both are eager. Count both in the item's expected effect, and keep any hero preload single (regressions R4).
- An eager hero exposed CLS on three stores (regressions R8). The Round must show no CLS loss.
- Callers that pass a media-condition `sizes` broke on a non-lazysizes path once and rendered empty product images (regressions R2). Read every caller before changing the snippet's signature.
- Collection pages (roughly the first four cards eager, by `forloop.index`) and the product gallery's first image were never measured in the retro. Plan them as their own item after the hero, carrying D1's fix as well, with the expected effect marked unmeasured.

**Measured effect.** The strongest lever in the retro.

- **Interleaved pairs, hero only** (D1, D2, D3 and a real `sizes`; three files, 48 lines): control 71, 72, 72, 71 against patched 89, 89, 89, 89, so **4 of 4 pairs, +17 to +18**, TBT unchanged. After going live the store's median moved from 64 (60–66, nine Samples) to 84 (79–90, nine Samples). PageSpeed Insights half an hour later still showed 35 and the old markup, so the change's PageSpeed effect is unverified.
- **Single Samples and bundles on other Golden stores:** 73 → 84 (single Sample, LCP 6.9 → 3.5 s); 52 → 71 inside a bundle (LCP 8.8 → 3.6 s); 59 → 75 interleaved inside a bundle (LCP 16.7 → 3.1 s); LCP 8–10 s → about 5 s; LCP 20.1 → 10.9 s.

## D3. The srcset loses its final width descriptor

**Fixed in Golden:** not yet

**What it is.** `responsive-image` builds its `srcset` with `unless forloop.last` between candidates, then still slices one character off the end:

```liquid
assign srcset_clean = srcset | strip | split: ',' | join: ', '
assign srcset_clean_length = srcset_clean | size | minus: 1
assign srcset_final = srcset_clean | slice: 0, srcset_clean_length
```

The slice removes the last candidate's `w`, so the largest image reads `…&width=1600 1600`, which browsers discard. It applies to `srcset` and `data-srcset` alike, so every image on every page loses its widest candidate.

**Detection.** After stripping Liquid comments, `responsive-image` still slices with `slice: 0, srcset_clean_length` and loops with `forloop.last`.

**Proven fix.** Replace the three lines with

```liquid
assign srcset_final = srcset | strip
```

**Measured effect.** Never isolated; it shipped inside the D2 wins. It is a correctness fix: Lighthouse's mobile phone (about 412 px wide at 1.75×, so about 721 px) picks the 800 w candidate either way, so expect little or no mobile change. Large and high-density desktop screens get their sharp image back. Plan it in the first D2 item.

## D4. The button snippet repeats its static CSS for every button

**Fixed in Golden:** not yet

**What it is.** `snippets/button.liquid` (a 14.8 KB file) wraps about 450 lines of fully static CSS in `{%- style -%}`. A `style` tag re-emits its body on every render, so each button on a page adds the same **12.1 KB** `<style data-shopify>` block to the HTML: measured at 12,102 bytes per instance, four instances on one home page. Fifteen sections, blocks and snippets render buttons.

**Detection.** After stripping Liquid comments, `snippets/button.liquid` holds a `style` block longer than 2,000 characters with no `{{` inside.

**Proven fix.** Swap the tag pair: `{%- style -%}` … `{%- endstyle -%}` becomes `{% stylesheet %}` … `{% endstylesheet %}`. A two-line diff. Shopify then serves the CSS once, in a cached file, and only for snippets rendered on the page. The block holds no Liquid, so nothing is lost. One store confirmed the buttons' computed styles were byte-identical afterwards. Moving the CSS from the body to a stylesheet can change which rule wins a specificity tie, and no check in the Round looks at styling: the smoke check does what a shopper does, and the pairs score speed. Once the Round is kept, the report's What changed carries a **Look before going live** note naming `snippets/button.liquid`, so the developer compares the buttons on the Working theme with the published theme's by eye before publishing.

**Measured effect.** Small. One store went 86 → 88 (single Samples, stacked on earlier changes) as its home HTML fell from 646 KB to 561 KB; another shed about 100 KB of HTML together with the image snippet's shared styles. Duplicated inline CSS compresses well on the wire (on one store, minifying 455 KB of it would have saved only 9 KB transferred), so the gain is HTML parsing and the bytes ahead of the hero. Expect +0 to +2, and order it after D2.
