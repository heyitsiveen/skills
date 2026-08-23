# A stand-in inherits the Target theme's fonts and nothing else

The composer prefers settings that inherit from global theme settings, so that a build stays wired into the theme's design system. `shopify-page-replicate` inverts that rule: colors, spacing, sizes, radii and borders are written as per-instance values matching the Source page. The single exception is the heading and body font families, which come from the Target theme's globals.

A Stand-in exists precisely because no new design exists for that page. Its numbers are the only design it has, and giving it the Target theme's numbers would be a design decision nobody made — and an unrecoverable one, because a page that never looked like its source cannot be restored without re-running. Font family is different: the revamp's type choice is already settled and already applies store-wide.

## Consequences

The fidelity forecast carries an override table naming every setting that departs from a Target theme global. That table is the unwind list for when the real design arrives.

The design spec's typography rows carry two families — the one measured on the Source page, and the Target theme global that replaces it. The style report asserts against the second. Without that, a deliberate font swap would report every heading on the page as a mismatch and bury the real ones.
