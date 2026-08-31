# The `export` field ships through PDF, because PNG and SVG carry the page behind the node

The Figma MCP's `download_assets` returns three things. `rawImages` hands back the designer's uploaded bytes and `svgAssets` hands back vector layers — both preserve alpha. `export` renders the node, and it renders it **with its whole ancestor chain**, clipped to the node's bounds. Where the design's page frame is filled, that fill lands behind the artwork.

An SVG export of a wordmark rectangle proves the mechanism: it arrives wrapped in `<rect width="1440" height="4461" fill="white"/>` — the page frame — with the wordmark's own image fill nested four groups deep. The PNG export of the same node is the same render, so it is 100% opaque. A bare hairline with no fill of its own exports opaque too. Passing `defaultFormat: "png"`, or omitting the overrides so the node's own export settings apply, changes nothing.

This is not Figma. Figma's own Export panel renders the same node transparent at the same settings. The compositing is introduced by the MCP.

Asking for `defaultFormat: "pdf"` returns the same crop with alpha intact. So `export` is requested as PDF and rasterized locally to the delivered format. The PDF is a transport format: it is never uploaded and never kept.

Requesting PDF is unconditional wherever `export` is used, rather than only where the inventory expects transparency. The bleed is not confined to transparent artwork — a fully opaque photograph in a node with a corner radius, a mask, or a drop shadow picks up the page fill in the gaps, and no one would have marked that photograph as needing transparency. A conditional rule fails exactly where the failure is hardest to see.

## Consequences

Assets divide by whether a crop exists, not by kind alone. A raster fill whose source aspect matches its node and which renders at 100% or less has no crop for `export` to contribute — it ships `rawImages` directly, and `export` would only upscale and flatten it. `export` is reached only for genuinely cropped fills and for compositions. The 2% aspect tolerance separating the two is a chosen line, not a derived one.

The `original-source-<name>` archive copy stays unconditional. Omitting it where the shipping file already is the original source was rejected: it makes the prefix's meaning depend on a row's crop status, so an absent archive would no longer be distinguishable from an uncropped row. A few duplicated kilobytes buy an invariant that holds by inspection.

Rasterizing adds a tool dependency the skills did not have. `sips` is used on macOS and ships with the OS; `pdftoppm` or `magick` covers other systems. The skills name both.

An alpha check closes the export phase: every asset the inventory marks as needing transparency must carry pixels below full opacity before it reaches `UPLOAD.md`. The defect this ADR records was invisible in every report the skills produced, because nothing measured it.

The asset inventory grows two columns to serve these rules — the largest `rawImages` entry's own w×h, which separates a cropped row from an uncropped one and caps the scale, and needs-transparency, which the alpha check asserts against. Both are measured at extraction rather than judged at export time.

The delivered format follows the artwork rather than the route — PNG where any pixel is transparent, JPEG where the picture is a fully opaque photograph, SVG for vectors. `rawImages` bytes are never re-encoded.
